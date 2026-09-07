#!/usr/bin/env python3
"""Remove only verified installations, preserving unrelated user configuration."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_fs import PLUGIN_NAME, json_bytes, json_object, require_owned, skill_names, transact
from install_codex import plugin_locations, resolve_home, skill_target


def bundled_skill_names(source_root: Path) -> list[str]:
    return skill_names(source_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("plugin", "skills"), default="plugin")
    parser.add_argument("--scope", choices=("user", "repo", "admin"), default="user")
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--home", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="Remove unmanaged or locally modified bundled targets; back them up first.")
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1],
                        help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        home = resolve_home(args.home)
        changes: dict[Path, Path | bytes | None] = {}
        if args.mode == "plugin":
            destination, marketplace, _ = plugin_locations(args.scope, home, args.repo_root)
            require_owned(destination, args.force)
            # Validate config before removing anything, including in dry-run mode.
            payload = json_object(marketplace, missing_ok=True)
            plugins = payload.get("plugins", [])
            if not isinstance(plugins, list):
                raise ValueError(f"{marketplace}: plugins must be a list")
            remaining = [item for item in plugins
                         if not (isinstance(item, dict) and item.get("name") == PLUGIN_NAME)]
            changes[destination] = None
            if len(remaining) != len(plugins):
                payload["plugins"] = remaining
                changes[marketplace] = json_bytes(payload)
        else:
            root = skill_target(args.scope, home, args.repo_root)
            for name in bundled_skill_names(args.source_root.expanduser().resolve()):
                destination = root / name
                require_owned(destination, args.force)
                changes[destination] = None
        transact(changes, dry_run=args.dry_run)
    except (OSError, ValueError) as exc:
        print(f"Uninstall failed: {exc}", file=sys.stderr)
        return 1
    print(f"{'Would remove' if args.dry_run else 'Removed'} {args.mode} ({args.scope} scope).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
