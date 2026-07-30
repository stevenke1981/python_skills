#!/usr/bin/env python3
"""Install this plugin or its skills into Codex-compatible locations."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

PLUGIN_NAME = "python-engineering-skills"
MARKETPLACE_NAME = "stevenke-python-plugins"


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_home(value: Path | None) -> Path:
    return (value or Path.home()).expanduser().resolve()


def resolve_repo_target(value: Path | None) -> Path:
    if value is None:
        raise ValueError("--repo-root is required when --scope repo is used")
    return value.expanduser().resolve()


def copy_tree_replace(source: Path, destination: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"replace {destination} <- {source}")
        return
    if destination.exists() or destination.is_symlink():
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        else:
            destination.unlink()
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        print(f"update {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def marketplace_entry(relative_plugin_path: str) -> dict[str, Any]:
    return {
        "name": PLUGIN_NAME,
        "source": {
            "source": "local",
            "path": relative_plugin_path,
        },
        "policy": {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        },
        "category": "Developer Tools",
    }


def merge_marketplace(path: Path, relative_plugin_path: str, dry_run: bool) -> None:
    payload = load_json_object(path)
    payload.setdefault("name", MARKETPLACE_NAME)
    payload.setdefault("interface", {"displayName": "StevenKe Python Plugins"})

    plugins = payload.get("plugins", [])
    if not isinstance(plugins, list):
        raise ValueError(f"{path}: plugins must be a list")
    plugins = [
        item
        for item in plugins
        if not (isinstance(item, dict) and item.get("name") == PLUGIN_NAME)
    ]
    plugins.append(marketplace_entry(relative_plugin_path))
    payload["plugins"] = plugins
    write_json(path, payload, dry_run)


def install_plugin(root: Path, scope: str, home: Path, repo_target: Path | None, dry_run: bool) -> list[Path]:
    source = root
    if scope == "user":
        destination = home / ".codex" / "plugins" / PLUGIN_NAME
        marketplace = home / ".agents" / "plugins" / "marketplace.json"
        relative_plugin_path = f"./.codex/plugins/{PLUGIN_NAME}"
    elif scope == "repo":
        target = resolve_repo_target(repo_target)
        destination = target / "plugins" / PLUGIN_NAME
        marketplace = target / ".agents" / "plugins" / "marketplace.json"
        relative_plugin_path = f"./plugins/{PLUGIN_NAME}"
    else:
        raise ValueError("plugin mode supports only user and repo scopes")

    if dry_run:
        print(f"replace {destination} with the plugin package from {source}")
    else:
        if destination.exists() or destination.is_symlink():
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source / ".codex-plugin", destination / ".codex-plugin")
        shutil.copytree(source / "skills", destination / "skills")
        for name in ("README.md", "CODEX_PLUGIN.md"):
            candidate = source / name
            if candidate.is_file():
                shutil.copy2(candidate, destination / name)

    merge_marketplace(marketplace, relative_plugin_path, dry_run)
    return [destination, marketplace]


def skill_target(scope: str, home: Path, repo_target: Path | None) -> Path:
    if scope == "user":
        return home / ".agents" / "skills"
    if scope == "repo":
        return resolve_repo_target(repo_target) / ".agents" / "skills"
    if scope == "admin":
        return Path("/etc/codex/skills")
    raise ValueError(f"unsupported scope: {scope}")


def install_skills(root: Path, scope: str, home: Path, repo_target: Path | None, dry_run: bool) -> list[Path]:
    destination_root = skill_target(scope, home, repo_target)
    installed: list[Path] = []
    source_root = root / "skills"
    for source in sorted(path for path in source_root.iterdir() if path.is_dir()):
        destination = destination_root / source.name
        copy_tree_replace(source, destination, dry_run)
        installed.append(destination)
    return installed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install the full plugin through a local marketplace or copy only its skills."
    )
    parser.add_argument("--mode", choices=("plugin", "skills"), default="plugin")
    parser.add_argument("--scope", choices=("user", "repo", "admin"), default="user")
    parser.add_argument("--repo-root", type=Path, help="Target repository when --scope repo is used.")
    parser.add_argument(
        "--home",
        type=Path,
        help="Override the user home directory. Intended for testing and controlled VM images.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=repository_root(),
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.source_root.expanduser().resolve()
    home = resolve_home(args.home)

    try:
        if args.mode == "plugin":
            paths = install_plugin(root, args.scope, home, args.repo_root, args.dry_run)
        else:
            paths = install_skills(root, args.scope, home, args.repo_root, args.dry_run)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1

    action = "Would install" if args.dry_run else "Installed"
    print(f"{action} {args.mode} ({args.scope} scope):")
    for path in paths:
        print(f"  - {path}")
    if args.mode == "plugin":
        print("Refresh ChatGPT or Codex, then install Python Engineering Skills from the local marketplace.")
    else:
        print("Start a new Codex session so the copied skills are rediscovered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
