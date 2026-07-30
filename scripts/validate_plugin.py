#!/usr/bin/env python3
"""Validate the installable Codex plugin, marketplace entry, and skill mirror."""

from __future__ import annotations

import argparse
import filecmp
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
PLUGIN_NAME = "python-engineering-skills"
REQUIRED_INSTALLERS = (
    "scripts/install_codex.py",
    "scripts/uninstall_codex.py",
    "scripts/install_codex.sh",
    "scripts/install_codex.ps1",
)


@dataclass(frozen=True, slots=True)
class Issue:
    level: str
    path: str
    message: str


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def issue(path: Path | str, message: str, level: str = "error") -> Issue:
    return Issue(level=level, path=str(path), message=message)


def load_json(path: Path, root: Path, issues: list[Issue]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        issues.append(issue(path.relative_to(root), "required file is missing"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(issue(path.relative_to(root), f"cannot parse JSON: {exc}"))
    return None


def resolve_relative_path(root: Path, value: str, field: str, path: Path, issues: list[Issue]) -> Path | None:
    if not value.startswith("./"):
        issues.append(issue(path.relative_to(root), f"{field} must use a ./ relative path"))
        return None
    resolved = (root / value[2:]).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        issues.append(issue(path.relative_to(root), f"{field} escapes the repository root"))
        return None
    return resolved


def validate_manifest(root: Path, issues: list[Issue]) -> dict[str, Any] | None:
    path = root / ".codex-plugin" / "plugin.json"
    payload = load_json(path, root, issues)
    if not isinstance(payload, dict):
        return None

    for field in ("name", "version", "description", "skills"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.append(issue(path.relative_to(root), f"{field} must be a non-empty string"))

    name = payload.get("name")
    if isinstance(name, str):
        if not NAME_RE.fullmatch(name):
            issues.append(issue(path.relative_to(root), "name must use lowercase letters, digits, and single hyphens"))
        if name != PLUGIN_NAME:
            issues.append(issue(path.relative_to(root), f"name must be {PLUGIN_NAME!r}"))

    version = payload.get("version")
    if isinstance(version, str) and not SEMVER_RE.fullmatch(version):
        issues.append(issue(path.relative_to(root), "version must be valid semantic versioning"))

    description = payload.get("description")
    if isinstance(description, str) and len(description) > 1024:
        issues.append(issue(path.relative_to(root), "description must not exceed 1024 characters"))

    skills = payload.get("skills")
    if isinstance(skills, str):
        skills_path = resolve_relative_path(root, skills, "skills", path, issues)
        if skills_path is not None and not skills_path.is_dir():
            issues.append(issue(path.relative_to(root), f"skills directory does not exist: {skills}"))

    return payload


def source_skill_names(root: Path, issues: list[Issue]) -> set[str]:
    path = root / "skills-manifest.json"
    payload = load_json(path, root, issues)
    names: set[str] = set()
    if not isinstance(payload, dict):
        return names

    entries = payload.get("skills")
    if not isinstance(entries, list):
        issues.append(issue(path.relative_to(root), "skills must be a list"))
        return names

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            issues.append(issue(path.relative_to(root), f"skills[{index}] must contain a string name"))
            continue
        names.add(entry["name"])
    return names


def relative_files(directory: Path) -> set[Path]:
    return {
        path.relative_to(directory)
        for path in directory.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def validate_skill_mirror(root: Path, issues: list[Issue]) -> None:
    expected = source_skill_names(root, issues)
    plugin_root = root / "skills"
    actual = {
        path.name
        for path in plugin_root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    } if plugin_root.is_dir() else set()

    for name in sorted(expected - actual):
        issues.append(issue("skills", f"missing plugin skill: {name}"))
    for name in sorted(actual - expected):
        issues.append(issue("skills", f"unexpected plugin skill: {name}"))

    for name in sorted(expected & actual):
        source = root / name
        destination = plugin_root / name
        if not source.is_dir():
            issues.append(issue(name, "source skill directory is missing"))
            continue

        source_files = relative_files(source)
        destination_files = relative_files(destination)
        for relative in sorted(source_files - destination_files):
            issues.append(issue(destination.relative_to(root), f"missing mirror file: {relative.as_posix()}"))
        for relative in sorted(destination_files - source_files):
            issues.append(issue(destination.relative_to(root), f"unexpected mirror file: {relative.as_posix()}"))
        for relative in sorted(source_files & destination_files):
            if not filecmp.cmp(source / relative, destination / relative, shallow=False):
                issues.append(issue(destination.relative_to(root), f"mirror differs: {relative.as_posix()}"))


def validate_marketplace(root: Path, manifest: dict[str, Any] | None, issues: list[Issue]) -> None:
    path = root / ".agents" / "plugins" / "marketplace.json"
    payload = load_json(path, root, issues)
    if not isinstance(payload, dict):
        return

    plugins = payload.get("plugins")
    if not isinstance(plugins, list):
        issues.append(issue(path.relative_to(root), "plugins must be a list"))
        return

    matching = [entry for entry in plugins if isinstance(entry, dict) and entry.get("name") == PLUGIN_NAME]
    if len(matching) != 1:
        issues.append(issue(path.relative_to(root), f"must contain exactly one {PLUGIN_NAME!r} entry"))
        return

    entry = matching[0]
    source = entry.get("source")
    if not isinstance(source, dict):
        issues.append(issue(path.relative_to(root), "plugin source must be an object"))
    else:
        if source.get("source") != "local":
            issues.append(issue(path.relative_to(root), "plugin source.source must be 'local'"))
        source_path = source.get("path")
        if not isinstance(source_path, str):
            issues.append(issue(path.relative_to(root), "plugin source.path must be a string"))
        else:
            plugin_root = resolve_relative_path(root, source_path, "source.path", path, issues)
            if plugin_root is not None and not (plugin_root / ".codex-plugin" / "plugin.json").is_file():
                issues.append(issue(path.relative_to(root), "local plugin source does not contain .codex-plugin/plugin.json"))

    policy = entry.get("policy")
    if not isinstance(policy, dict):
        issues.append(issue(path.relative_to(root), "plugin policy must be an object"))
    else:
        if policy.get("installation") not in {"AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"}:
            issues.append(issue(path.relative_to(root), "policy.installation is invalid"))
        if policy.get("authentication") not in {"ON_INSTALL", "ON_USE"}:
            issues.append(issue(path.relative_to(root), "policy.authentication is invalid"))

    category = entry.get("category")
    if not isinstance(category, str) or not category.strip():
        issues.append(issue(path.relative_to(root), "plugin category must be a non-empty string"))

    if manifest is not None and entry.get("name") != manifest.get("name"):
        issues.append(issue(path.relative_to(root), "marketplace and plugin manifest names differ"))


def validate_installers(root: Path, issues: list[Issue]) -> None:
    for relative in REQUIRED_INSTALLERS:
        path = root / relative
        if not path.is_file():
            issues.append(issue(relative, "required installer file is missing"))


def validate_repository(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    manifest = validate_manifest(root, issues)
    validate_skill_mirror(root, issues)
    validate_marketplace(root, manifest, issues)
    validate_installers(root, issues)
    return issues


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the Codex plugin package.")
    parser.add_argument(
        "--root",
        type=Path,
        default=repository_root(),
        help="Repository root. Defaults to the parent of this script directory.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.expanduser().resolve()
    issues = validate_repository(root)

    if args.json:
        print(json.dumps([asdict(item) for item in issues], ensure_ascii=False, indent=2))
    elif issues:
        print("Codex plugin validation failed:", file=sys.stderr)
        for item in issues:
            print(f"  [{item.level}] {item.path}: {item.message}", file=sys.stderr)
    else:
        print("Codex plugin validation passed.")

    return 1 if any(item.level == "error" for item in issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
