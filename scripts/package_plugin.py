#!/usr/bin/env python3
"""Build a self-contained deterministic installer ZIP and its SHA-256 checksum."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_fs import bundled_skills, json_object, plain_path, tree_files

FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
INCLUDED_FILES = (
    ".agents/plugins/marketplace.json", "CODEX_PLUGIN.md", "README.md",
    "skills-manifest.json", "scripts/codex_fs.py", "scripts/install_codex.py",
    "scripts/uninstall_codex.py", "scripts/install_codex.ps1", "scripts/install_codex.sh",
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_validator(root: Path):
    path = root / "scripts/validate_plugin.py"
    spec = importlib.util.spec_from_file_location("validate_plugin", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load validator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def plugin_metadata(root: Path) -> tuple[str, str]:
    payload = json_object(root / ".codex-plugin/plugin.json")
    return payload["name"], payload["version"]


def package_paths(root: Path) -> list[Path]:
    bundled_skills(root)
    paths: list[Path] = []
    for directory in (root / ".codex-plugin", root / "skills"):
        paths.extend(tree_files(directory))
    for relative in INCLUDED_FILES:
        path = root / relative
        plain_path(path)
        if not path.is_file():
            raise ValueError(f"Required distribution file is missing: {relative}")
        paths.append(path)
    return sorted(set(paths), key=lambda p: p.relative_to(root).as_posix())


def write_zip(root: Path, output: Path) -> None:
    paths = package_paths(root)  # Check all inputs before touching an existing artifact.
    plain_path(output)
    # A custom output must never overwrite a source or enter packaged directories.
    if (output.resolve() in {p.resolve() for p in paths}
            or any((root / d).resolve() in output.resolve().parents
                   for d in ("skills", ".codex-plugin", "scripts"))):
        raise ValueError("Output would overwrite or contaminate package sources")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".python-skills-zip-", dir=output.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in paths:
                info = zipfile.ZipInfo(path.relative_to(root).as_posix(), FIXED_TIMESTAMP)
                info.create_system = 3  # Unix metadata, also when building on Windows.
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o100755 if path.suffix in {".sh", ".py"} else 0o100644) << 16
                archive.writestr(info, path.read_bytes(), compresslevel=9)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repository_root())
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = args.root.expanduser().resolve()
        issues = load_validator(root).validate_repository(root)
        errors = [item for item in issues if item.level == "error"]
        if errors:
            raise ValueError("Invalid plugin:\n" + "\n".join(f"{x.path}: {x.message}" for x in errors))
        name, version = plugin_metadata(root)
        # Keep the last component unresolved so output symlinks are rejected.
        output = Path(os.path.abspath(args.output.expanduser())) if args.output else root / "dist" / f"{name}-{version}.zip"
        checksum = output.with_suffix(output.suffix + ".sha256")
        plain_path(checksum)
        write_zip(root, output)
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        checksum.write_text(f"{digest}  {output.name}\n", encoding="utf-8")
        print(output)
        print(checksum)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Packaging failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
