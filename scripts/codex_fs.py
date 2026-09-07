"""Shared, standard-library-only filesystem safety for the Codex installers.

Operations must be serialized by the caller. Rollback handles Python/I/O errors,
not power loss or hostile concurrent changes to the filesystem.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any

PLUGIN_NAME = "python-engineering-skills"
RECEIPT = ".python-skills-install.json"
NAME_RE = re.compile(r"py-[a-z0-9]+(?:-[a-z0-9]+)*\Z")
IGNORED = {"__pycache__", ".DS_Store"}


def plain_path(path: Path) -> None:
    """Reject symlinks/reparse points, including dangling links and parents."""
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Refusing linked/reparse-point path: {item}")


def tree_files(root: Path) -> list[Path]:
    plain_path(root)
    if not root.is_dir():
        raise ValueError(f"Required directory is missing: {root}")
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        plain_path(path)
        mode = path.stat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise ValueError(f"Refusing special file: {path}")
        if stat.S_ISREG(mode) and not any(p in IGNORED for p in path.relative_to(root).parts):
            files.append(path)
    return files


def json_object(path: Path, *, missing_ok: bool = False) -> dict[str, Any]:
    plain_path(path)
    if missing_ok and not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


def json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def skill_names(root: Path) -> list[str]:
    entries = json_object(root / "skills-manifest.json").get("skills")
    if not isinstance(entries, list) or not entries:
        raise ValueError("skills-manifest.json: skills must be a non-empty list")
    names: list[str] = []
    for entry in entries:
        name = entry.get("name") if isinstance(entry, dict) else None
        if not isinstance(name, str) or len(name) > 64 or not NAME_RE.fullmatch(name):
            raise ValueError(f"Invalid or unsafe skill name: {name!r}")
        if name in names:
            raise ValueError(f"Duplicate skill name: {name}")
        names.append(name)
    return sorted(names)


def bundled_skills(root: Path) -> list[Path]:
    names = skill_names(root)
    base = root / "skills"
    tree_files(base)
    actual = {p.name for p in base.iterdir() if p.is_dir()}
    if actual != set(names):
        raise ValueError("skills/ directories do not match skills-manifest.json")
    for name in names:
        if not (base / name / "SKILL.md").is_file():
            raise ValueError(f"Missing skills/{name}/SKILL.md")
    return [base / name for name in names]


def disjoint(source: Path, target: Path) -> None:
    source, target = source.resolve(), target.resolve()
    if source == target or source in target.parents or target in source.parents:
        raise ValueError(f"Source and destination overlap: {source} / {target}")


def hashes(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in tree_files(root) if p != root / RECEIPT}


def require_owned(path: Path, force: bool) -> None:
    plain_path(path)
    if not path.exists():
        return
    tree_files(path)
    if force:
        return
    try:
        receipt = json_object(path / RECEIPT)
    except (OSError, ValueError) as exc:
        raise ValueError(f"Unmanaged installation: {path}; back it up and use --force to replace/remove it") from exc
    if (receipt.get("owner") != PLUGIN_NAME or receipt.get("schema_version") != 1
            or receipt.get("files") != hashes(path)):
        raise ValueError(f"Locally modified installation: {path}; back it up before using --force")


def _remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def transact(changes: dict[Path, Path | bytes | None], *, dry_run: bool = False,
             owned: frozenset[Path] = frozenset()) -> None:
    """Stage ALL payloads before replacing any target; restore backups on error.

    A Path payload is a directory, bytes is a file, and None is a deletion.
    Unique sibling staging directories keep renames on the same filesystem.
    """
    targets = list(changes)
    for i, target in enumerate(targets):
        plain_path(target)
        for other in targets[:i]:
            if target in other.parents or other in target.parents:
                raise ValueError(f"Overlapping transaction targets: {target} / {other}")
        source = changes[target]
        if isinstance(source, Path):
            tree_files(source)
            disjoint(source, target)
    if dry_run:
        for target, source in changes.items():
            print(f"{'remove' if source is None else 'replace'} {target}")
        return
    records: list[dict[str, Any]] = []
    preserve_backups = False
    try:
        for target, source in changes.items():
            if source is None and not target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            work = Path(tempfile.mkdtemp(prefix=".python-skills-txn-", dir=target.parent))
            record = dict(target=target, work=work, old=False, new=False, source=source)
            records.append(record)
            staged = work / "new"
            if isinstance(source, Path):
                shutil.copytree(source, staged, ignore=shutil.ignore_patterns(*IGNORED))
                if target in owned:
                    (staged / RECEIPT).write_bytes(json_bytes({
                        "owner": PLUGIN_NAME, "schema_version": 1, "files": hashes(staged)}))
            elif isinstance(source, bytes):
                staged.write_bytes(source)
                if target.is_file():
                    staged.chmod(stat.S_IMODE(target.stat().st_mode))
        for record in records:
            target, work = record["target"], record["work"]
            plain_path(target)
            if target.exists():
                os.replace(target, work / "old")
                record["old"] = True
            if record["source"] is not None:
                os.replace(work / "new", target)
                record["new"] = True
    except BaseException as exc:
        recovery_errors: list[str] = []
        for record in reversed(records):
            try:
                if record["new"]:
                    _remove(record["target"])
                if record["old"]:
                    os.replace(record["work"] / "old", record["target"])
            except OSError as recovery:
                recovery_errors.append(f"{record['work']}: {recovery}")
        if recovery_errors:
            preserve_backups = True
            raise OSError("Rollback incomplete; retain these recovery folders: " + "; ".join(recovery_errors)) from exc
        raise
    finally:
        if not preserve_backups:
            for record in records:
                shutil.rmtree(record["work"], ignore_errors=True)
