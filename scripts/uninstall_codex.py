#!/usr/bin/env python3
"""Remove this plugin or its skills while preserving unrelated Codex configuration."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

PLUGIN_NAME = "python-engineering-skills"


def resolve_home(value: Path | None) -> Path:
    return (value or Path.home()).expanduser().resolve()


def resolve_repo_target(value: Path | None) -> Path:
    if value is None:
        raise ValueError("--repo-root is required when --scope repo is used")
    return value.expanduser().resolve()


def remove_path(path: Path, dry_run: bool) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if dry_run:
        print(f"remove {path}")
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def update_marketplace(path: Path, dry_run: bool) -> None:
    if not path.exists():
        return
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    plugins = payload.get("plugins", [])
    if not isinstance(plugins, list):
        raise ValueError(f"{path}: plugins must be a list")
    remaining = [
        item
        for item in plugins
        if not (isinstance(item, dict) and item.get("name") == PLUGIN_NAME)
    ]
    if len(remaining) == len(plugins):
        return
    payload["plugins"] = remaining
    if dry_run:
        print(f"update {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def plugin_locations(scope: str, home: Path, repo_root: Path | None) -> tuple[Path, Path]:
    if scope == "user":
        return (
            home / ".codex" / "plugins" / PLUGIN_NAME,
            home / ".agents" / "plugins" / "marketplace.json",
        )
    if scope == "repo":
        target = resolve_repo_target(repo_root)
        return (
            target / "plugins" / PLUGIN_NAME,
            target / ".agents" / "plugins" / "marketplace.json",
        )
    raise ValueError("plugin mode supports only user and repo scopes")


def skills_root(scope: str, home: Path, repo_root: Path | None) -> Path:
    if scope == "user":
        return home / ".agents" / "skills"
    if scope == "repo":
        return resolve_repo_target(repo_root) / ".agents" / "skills"
    if scope == "admin":
        return Path("/etc/codex/skills")
    raise ValueError(f"unsupported scope: {scope}")


def bundled_skill_names(source_root: Path) -> list[str]:
    path = source_root / "skills-manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("skills", [])
    return sorted(entry["name"] for entry in entries if isinstance(entry, dict) and isinstance(entry.get("name"), str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Uninstall Python Engineering Skills.")
    parser.add_argument("--mode", choices=("plugin", "skills"), default="plugin")
    parser.add_argument("--scope", choices=("user", "repo", "admin"), default="user")
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--home", type=Path, help="Override the user home directory.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    home = resolve_home(args.home)
    source_root = args.source_root.expanduser().resolve()

    try:
        removed: list[Path] = []
        if args.mode == "plugin":
            destination, marketplace = plugin_locations(args.scope, home, args.repo_root)
            remove_path(destination, args.dry_run)
            update_marketplace(marketplace, args.dry_run)
            removed.append(destination)
        else:
            root = skills_root(args.scope, home, args.repo_root)
            for name in bundled_skill_names(source_root):
                destination = root / name
                remove_path(destination, args.dry_run)
                removed.append(destination)
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(f"Uninstall failed: {exc}", file=sys.stderr)
        return 1

    action = "Would remove" if args.dry_run else "Removed"
    print(f"{action} {args.mode} ({args.scope} scope):")
    for path in removed:
        print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
