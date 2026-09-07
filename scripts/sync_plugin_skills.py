#!/usr/bin/env python3
"""Synchronize the skill mirror only after validating every maintained source."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_fs import IGNORED, NAME_RE, plain_path, skill_names, transact, tree_files


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def source_skill_dirs(root: Path) -> list[Path]:
    names = skill_names(root)
    actual = {p.name for p in root.glob("py-*") if p.is_dir()}
    if actual != set(names):
        raise ValueError("Root py-* directories do not match skills-manifest.json; refusing to synchronize")
    sources = [root / name for name in names]
    for source in sources:
        tree_files(source)
        if not (source / "SKILL.md").is_file():
            raise ValueError(f"Missing source SKILL.md: {source}")
    return sources


def relative_files(directory: Path) -> set[Path]:
    return {p.relative_to(directory) for p in tree_files(directory)}


def compare_skill(source: Path, destination: Path) -> list[str]:
    plain_path(destination)
    if not destination.is_dir():
        return [f"missing plugin skill directory: {destination.name}"]
    src, dst = relative_files(source), relative_files(destination)
    issues = [f"{destination.name}: missing {p.as_posix()}" for p in sorted(src - dst)]
    issues += [f"{destination.name}: unexpected {p.as_posix()}" for p in sorted(dst - src)]
    issues += [f"{destination.name}: content differs for {p.as_posix()}" for p in sorted(src & dst)
               if (source / p).read_bytes() != (destination / p).read_bytes()]
    return issues


def mirror_entries(root: Path) -> list[Path]:
    destination = root / "skills"
    plain_path(destination)
    if not destination.exists():
        return []
    tree_files(destination)
    return [p for p in sorted(destination.iterdir()) if p.name not in IGNORED]


def check_sync(root: Path) -> list[str]:
    sources = source_skill_dirs(root)
    names = {p.name for p in sources}
    issues = [f"unexpected plugin entry: {p.name}" for p in mirror_entries(root)
              if p.name not in names or not p.is_dir()]
    for source in sources:
        issues.extend(compare_skill(source, root / "skills" / source.name))
    return issues


def synchronize(root: Path, clean: bool = True) -> list[str]:
    sources = source_skill_dirs(root)  # Never create/delete a mirror before this succeeds.
    names = {p.name for p in sources}
    changes: dict[Path, Path | bytes | None] = {}
    for path in mirror_entries(root):
        if path.name not in names and clean:
            if not path.is_dir() or not NAME_RE.fullmatch(path.name):
                raise ValueError(f"Refusing to delete unrelated mirror entry: {path}")
            changes[path] = None
    for source in sources:
        destination = root / "skills" / source.name
        if not destination.exists() or compare_skill(source, destination):
            changes[destination] = source
    transact(changes)
    return [p.name for p in sources]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repository_root())
    parser.add_argument("--check", action="store_true", help="Check without modifying any files.")
    parser.add_argument("--no-clean", action="store_true", help="Keep extra mirror entries.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = args.root.expanduser().resolve()
        if args.check:
            issues = check_sync(root)
            if issues:
                raise ValueError("Plugin skill mirror is out of date:\n  - " + "\n  - ".join(issues))
            print("Plugin skill mirror is current.")
        else:
            print(f"Synchronized {len(synchronize(root, clean=not args.no_clean))} skills.")
    except (OSError, ValueError) as exc:
        print(f"Synchronization failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
