#!/usr/bin/env python3
"""Synchronize root py-* skill sources into the installable plugin skills directory."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

SKILL_PREFIX = "py-"
IGNORED_NAMES = {".DS_Store", "__pycache__"}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def source_skill_dirs(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.iterdir()
        if path.is_dir() and path.name.startswith(SKILL_PREFIX) and (path / "SKILL.md").is_file()
    )


def relative_files(directory: Path) -> set[Path]:
    return {
        path.relative_to(directory)
        for path in directory.rglob("*")
        if path.is_file() and not any(part in IGNORED_NAMES for part in path.parts)
    }


def compare_skill(source: Path, destination: Path) -> list[str]:
    issues: list[str] = []
    if not destination.is_dir():
        return [f"missing plugin skill directory: {destination.relative_to(destination.parents[1])}"]

    source_files = relative_files(source)
    destination_files = relative_files(destination)

    for relative in sorted(source_files - destination_files):
        issues.append(f"{destination.name}: missing {relative.as_posix()}")
    for relative in sorted(destination_files - source_files):
        issues.append(f"{destination.name}: unexpected {relative.as_posix()}")
    for relative in sorted(source_files & destination_files):
        if not filecmp.cmp(source / relative, destination / relative, shallow=False):
            issues.append(f"{destination.name}: content differs for {relative.as_posix()}")
    return issues


def check_sync(root: Path) -> list[str]:
    destination_root = root / "skills"
    sources = source_skill_dirs(root)
    source_names = {path.name for path in sources}
    destination_names = {
        path.name
        for path in destination_root.iterdir()
        if path.is_dir()
    } if destination_root.is_dir() else set()

    issues: list[str] = []
    for name in sorted(source_names - destination_names):
        issues.append(f"missing plugin skill: {name}")
    for name in sorted(destination_names - source_names):
        issues.append(f"unexpected plugin skill: {name}")
    for source in sources:
        destination = destination_root / source.name
        if destination.exists():
            issues.extend(compare_skill(source, destination))
    return issues


def synchronize(root: Path, clean: bool = True) -> list[str]:
    destination_root = root / "skills"
    destination_root.mkdir(parents=True, exist_ok=True)

    sources = source_skill_dirs(root)
    source_names = {path.name for path in sources}

    if clean:
        for destination in destination_root.iterdir():
            if destination.is_dir() and destination.name not in source_names:
                shutil.rmtree(destination)

    copied: list[str] = []
    for source in sources:
        destination = destination_root / source.name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        copied.append(source.name)
    return copied


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Copy root py-* skill sources into skills/ or verify that the mirror is current."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=repository_root(),
        help="Repository root. Defaults to the parent of this script directory.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not modify files; fail when skills/ differs from the root py-* sources.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Keep unrelated directories already present under skills/.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.expanduser().resolve()

    if args.check:
        issues = check_sync(root)
        if issues:
            print("Plugin skill mirror is out of date:", file=sys.stderr)
            for issue in issues:
                print(f"  - {issue}", file=sys.stderr)
            return 1
        print("Plugin skill mirror is current.")
        return 0

    copied = synchronize(root, clean=not args.no_clean)
    if not copied:
        print("No root py-* skills were found.", file=sys.stderr)
        return 1
    print(f"Synchronized {len(copied)} skills into {root / 'skills'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
