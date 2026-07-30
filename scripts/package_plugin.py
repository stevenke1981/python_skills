#!/usr/bin/env python3
"""Build a deterministic ZIP archive for the installable Codex plugin."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
INCLUDED_FILES = (
    ".agents/plugins/marketplace.json",
    "CODEX_PLUGIN.md",
    "README.md",
    "scripts/install_codex.py",
    "scripts/uninstall_codex.py",
    "scripts/install_codex.ps1",
    "scripts/install_codex.sh",
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_validator(root: Path):
    path = root / "scripts" / "validate_plugin.py"
    spec = importlib.util.spec_from_file_location("validate_plugin", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load validator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def plugin_metadata(root: Path) -> tuple[str, str]:
    path = root / ".codex-plugin" / "plugin.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["name"], payload["version"]


def package_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for directory in (root / ".codex-plugin", root / "skills"):
        paths.extend(path for path in directory.rglob("*") if path.is_file())
    for relative in INCLUDED_FILES:
        path = root / relative
        if path.is_file():
            paths.append(path)
    return sorted(set(paths), key=lambda item: item.relative_to(root).as_posix())


def write_zip(root: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in package_paths(root):
            relative = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(relative, FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.suffix in {".sh", ".py"} else 0o644) << 16
            archive.writestr(info, path.read_bytes())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and package the Codex plugin.")
    parser.add_argument(
        "--root",
        type=Path,
        default=repository_root(),
        help="Repository root. Defaults to the parent of this script directory.",
    )
    parser.add_argument("--output", type=Path, help="ZIP path. Defaults to dist/<name>-<version>.zip.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.expanduser().resolve()
    validator = load_validator(root)
    issues = validator.validate_repository(root)
    errors = [item for item in issues if item.level == "error"]
    if errors:
        print("Refusing to package an invalid plugin:", file=sys.stderr)
        for item in errors:
            print(f"  - {item.path}: {item.message}", file=sys.stderr)
        return 1

    name, version = plugin_metadata(root)
    output = args.output.expanduser().resolve() if args.output else root / "dist" / f"{name}-{version}.zip"
    write_zip(root, output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
