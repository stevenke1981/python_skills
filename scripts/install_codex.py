#!/usr/bin/env python3
"""Install a validated bundle without silently destroying existing user files."""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

# Also support importlib-based tests and execution from outside the repository.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_fs import (PLUGIN_NAME, bundled_skills, disjoint, json_bytes,
                      json_object, plain_path, require_owned, transact, tree_files)

MARKETPLACE_NAME = "stevenke-python-plugins"
RUNTIME_FILES = ("install_codex.py", "uninstall_codex.py", "codex_fs.py",
                 "install_codex.sh", "install_codex.ps1")


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_home(value: Path | None) -> Path:
    return (value or Path.home()).expanduser().resolve()


def resolve_repo_target(value: Path | None) -> Path:
    if value is None:
        raise ValueError("--repo-root is required when --scope repo is used")
    return value.expanduser().resolve()


def plugin_locations(scope: str, home: Path, repo_target: Path | None) -> tuple[Path, Path, str]:
    if scope == "user":
        base, relative = home, f"./.codex/plugins/{PLUGIN_NAME}"
    elif scope == "repo":
        base, relative = resolve_repo_target(repo_target), f"./plugins/{PLUGIN_NAME}"
    else:
        raise ValueError("plugin mode supports only user and repo scopes")
    return base / relative[2:], base / ".agents/plugins/marketplace.json", relative


def skill_target(scope: str, home: Path, repo_target: Path | None) -> Path:
    if scope == "user":
        return home / ".agents/skills"
    if scope == "repo":
        return resolve_repo_target(repo_target) / ".agents/skills"
    if scope == "admin":
        if os.name == "nt":
            raise ValueError("admin scope is Unix-only; use --scope user or repo on Windows")
        return Path("/etc").resolve() / "codex/skills"
    raise ValueError(f"unsupported scope: {scope}")


def marketplace_entry(relative_plugin_path: str) -> dict[str, Any]:
    return {"name": PLUGIN_NAME,
            "source": {"source": "local", "path": relative_plugin_path},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Developer Tools"}


def marketplace_payload(path: Path, relative: str) -> dict[str, Any]:
    payload = json_object(path, missing_ok=True)
    plugins = payload.get("plugins", [])
    if not isinstance(plugins, list):
        raise ValueError(f"{path}: plugins must be a list")
    payload.setdefault("name", MARKETPLACE_NAME)
    payload.setdefault("interface", {"displayName": "StevenKe Python Plugins"})
    payload["plugins"] = [item for item in plugins
                          if not (isinstance(item, dict) and item.get("name") == PLUGIN_NAME)]
    payload["plugins"].append(marketplace_entry(relative))
    return payload


def install_plugin(root: Path, scope: str, home: Path, repo_target: Path | None,
                   dry_run: bool, force: bool = False) -> list[Path]:
    destination, marketplace, relative = plugin_locations(scope, home, repo_target)
    plain_path(destination)
    disjoint(root, destination)
    bundled_skills(root)
    manifest = json_object(root / ".codex-plugin/plugin.json")
    if manifest.get("name") != PLUGIN_NAME or manifest.get("skills") != "./skills/":
        raise ValueError("Invalid plugin name or skills path in plugin.json")
    tree_files(root / ".codex-plugin")
    require_owned(destination, force)
    # Parse shared configuration BEFORE staging or touching the installed copy.
    payload = marketplace_payload(marketplace, relative)
    for name in RUNTIME_FILES:
        path = root / "scripts" / name
        plain_path(path)
        if not path.is_file():
            raise ValueError(f"Missing runtime file: {path}")
    for name in ("README.md", "CODEX_PLUGIN.md"):
        plain_path(root / name)
    if dry_run:
        print(f"replace {destination}; update {marketplace}")
        return [destination, marketplace]
    with tempfile.TemporaryDirectory(prefix="python-skills-payload-") as temporary:
        staged = Path(temporary).resolve()
        for name in (".codex-plugin", "skills"):
            shutil.copytree(root / name, staged / name)
        (staged / "scripts").mkdir()
        for name in RUNTIME_FILES:
            shutil.copy2(root / "scripts" / name, staged / "scripts" / name)
        for name in ("README.md", "CODEX_PLUGIN.md", "skills-manifest.json"):
            if (root / name).is_file():
                shutil.copy2(root / name, staged / name)
        transact({destination: staged, marketplace: json_bytes(payload)},
                 owned=frozenset({destination}))
    return [destination, marketplace]


def install_skills(root: Path, scope: str, home: Path, repo_target: Path | None,
                   dry_run: bool, force: bool = False) -> list[Path]:
    sources = bundled_skills(root)
    destination_root = skill_target(scope, home, repo_target)
    changes: dict[Path, Path | bytes | None] = {}
    for source in sources:
        destination = destination_root / source.name
        plain_path(destination)
        disjoint(root, destination)
        require_owned(destination, force)
        changes[destination] = source
    transact(changes, dry_run=dry_run, owned=frozenset(changes))
    return list(changes)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("plugin", "skills"), default="plugin")
    parser.add_argument("--scope", choices=("user", "repo", "admin"), default="user")
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--home", type=Path, help="Override user home for testing or VM images.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and preview; do not write files.")
    parser.add_argument("--force", action="store_true",
                        help="Replace unmanaged or modified bundled targets; back them up first.")
    parser.add_argument("--source-root", type=Path, default=repository_root(), help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root, home = args.source_root.expanduser().resolve(), resolve_home(args.home)
        install = install_plugin if args.mode == "plugin" else install_skills
        paths = install(root, args.scope, home, args.repo_root, args.dry_run, args.force)
    except (OSError, ValueError) as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1
    print(f"{'Would install' if args.dry_run else 'Installed'} {args.mode} ({args.scope} scope):")
    for path in paths:
        print(f"  - {path}")
    if not args.dry_run:
        print("Start a new Codex session. Plugin mode also requires installation from the local marketplace.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
