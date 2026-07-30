#!/usr/bin/env python3
"""Validate this repository's Agent Skills structure without third-party packages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:\s*(.*))?$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
USER_PATH_RE = re.compile(
    r"(?:^|[\s`'\"])(?:/home/[^/\s]+/|/mnt/(?:data|user-data)/|[A-Za-z]:\\Users\\[^\\\s]+\\)"
)
REQUIRED_HEADINGS = (
    "## 執行流程",
    "## 交付標準",
    "## 延伸閱讀",
    "## 版本相容性",
)
REQUIRED_REFERENCES = (
    "references/examples.md",
    "references/cheatsheet.md",
    "references/pitfalls.md",
)


@dataclass(frozen=True, slots=True)
class Issue:
    level: str
    path: str
    message: str


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, str], str]:
    """Parse the top-level scalar fields needed by this validator."""
    normalized = text.lstrip("\ufeff")
    lines = normalized.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: SKILL.md must start with YAML frontmatter")

    try:
        closing = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        )
    except StopIteration as exc:
        raise ValueError(f"{path}: YAML frontmatter is not closed") from exc

    frontmatter = lines[1:closing]
    fields: dict[str, str] = {}
    index = 0

    while index < len(frontmatter):
        line = frontmatter[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if line.startswith((" ", "\t")):
            index += 1
            continue

        match = FIELD_RE.match(line)
        if not match:
            raise ValueError(f"{path}: invalid frontmatter line: {line!r}")

        key, raw_value = match.groups()
        value = (raw_value or "").strip()

        if value in {">", ">-", ">+", "|", "|-", "|+"}:
            block_lines: list[str] = []
            index += 1
            while index < len(frontmatter):
                block_line = frontmatter[index]
                if block_line and not block_line.startswith((" ", "\t")):
                    break
                block_lines.append(block_line.lstrip())
                index += 1

            if value.startswith(">"):
                value = " ".join(
                    part.strip() for part in block_lines if part.strip()
                )
            else:
                value = "\n".join(block_lines).strip()
            fields[key] = value
            continue

        fields[key] = _unquote(value)
        index += 1

    body = "\n".join(lines[closing + 1 :]).lstrip("\n")
    return fields, body


def _relative_link_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if not target or target.startswith(
        ("#", "http://", "https://", "mailto:", "data:")
    ):
        return None
    if " " in target and not target.startswith("<"):
        target = target.split(maxsplit=1)[0]
    target = target.strip("<>")
    return target.split("#", maxsplit=1)[0] or None


def validate_skill(skill_dir: Path, root: Path) -> list[Issue]:
    issues: list[Issue] = []
    skill_file = skill_dir / "SKILL.md"
    relative_skill_file = skill_file.relative_to(root)

    try:
        text = skill_file.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            Issue("error", str(relative_skill_file), f"cannot read file: {exc}")
        ]

    try:
        fields, body = parse_frontmatter(text, relative_skill_file)
    except ValueError as exc:
        return [Issue("error", str(relative_skill_file), str(exc))]

    name = fields.get("name", "")
    description = fields.get("description", "")
    compatibility = fields.get("compatibility", "")

    if not name:
        issues.append(
            Issue("error", str(relative_skill_file), "missing frontmatter name")
        )
    elif not NAME_RE.fullmatch(name):
        issues.append(
            Issue(
                "error",
                str(relative_skill_file),
                "name must contain lowercase letters, digits, and single hyphens only",
            )
        )
    elif name != skill_dir.name:
        issues.append(
            Issue(
                "error",
                str(relative_skill_file),
                f"name {name!r} must match parent directory {skill_dir.name!r}",
            )
        )

    if not description.strip():
        issues.append(
            Issue("error", str(relative_skill_file), "missing description")
        )
    elif len(description) > 1024:
        issues.append(
            Issue(
                "error",
                str(relative_skill_file),
                f"description has {len(description)} characters; maximum is 1024",
            )
        )
    elif len(description.split()) < 8:
        issues.append(
            Issue(
                "warning",
                str(relative_skill_file),
                "description is unusually short and may trigger poorly",
            )
        )

    if compatibility and len(compatibility) > 500:
        issues.append(
            Issue(
                "error",
                str(relative_skill_file),
                f"compatibility has {len(compatibility)} characters; maximum is 500",
            )
        )

    line_count = len(text.splitlines())
    if line_count > 500:
        issues.append(
            Issue(
                "error",
                str(relative_skill_file),
                f"SKILL.md has {line_count} lines; project limit is 500",
            )
        )

    for heading in REQUIRED_HEADINGS:
        if heading not in body:
            issues.append(
                Issue(
                    "error",
                    str(relative_skill_file),
                    f"missing required heading: {heading}",
                )
            )

    for relative_reference in REQUIRED_REFERENCES:
        reference = skill_dir / relative_reference
        if not reference.is_file():
            issues.append(
                Issue(
                    "error",
                    str(relative_skill_file),
                    f"missing required reference: {relative_reference}",
                )
            )

    for match in LINK_RE.finditer(body):
        target = _relative_link_target(match.group(1))
        if target is None:
            continue
        linked_path = (skill_dir / target).resolve()
        try:
            linked_path.relative_to(skill_dir.resolve())
        except ValueError:
            issues.append(
                Issue(
                    "error",
                    str(relative_skill_file),
                    f"relative link escapes the skill directory: {target}",
                )
            )
            continue
        if not linked_path.exists():
            issues.append(
                Issue(
                    "error",
                    str(relative_skill_file),
                    f"broken relative link: {target}",
                )
            )

    if sum(
        1 for line in body.splitlines() if line.lstrip().startswith("```")
    ) % 2:
        issues.append(
            Issue("error", str(relative_skill_file), "unbalanced fenced code block")
        )

    if USER_PATH_RE.search(body):
        issues.append(
            Issue(
                "error",
                str(relative_skill_file),
                "contains a user-specific absolute path; use project-relative examples",
            )
        )

    if "TODO" in body or "FIXME" in body:
        issues.append(
            Issue("warning", str(relative_skill_file), "contains TODO or FIXME text")
        )

    return issues


def load_json(path: Path, root: Path, issues: list[Issue]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        issues.append(
            Issue("error", str(path.relative_to(root)), "required file is missing")
        )
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(
            Issue(
                "error",
                str(path.relative_to(root)),
                f"cannot parse JSON: {exc}",
            )
        )
    return None


def validate_manifest(
    root: Path, skill_names: set[str], issues: list[Issue]
) -> None:
    manifest_path = root / "skills-manifest.json"
    manifest = load_json(manifest_path, root, issues)
    if not isinstance(manifest, dict):
        return

    entries = manifest.get("skills")
    if not isinstance(entries, list):
        issues.append(
            Issue("error", "skills-manifest.json", "skills must be a list")
        )
        return

    manifest_names: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            issues.append(
                Issue(
                    "error",
                    "skills-manifest.json",
                    f"skills[{index}] must contain a string name",
                )
            )
            continue
        manifest_names.append(entry["name"])

    if len(manifest_names) != len(set(manifest_names)):
        issues.append(
            Issue(
                "error",
                "skills-manifest.json",
                "contains duplicate skill names",
            )
        )

    missing = skill_names - set(manifest_names)
    extra = set(manifest_names) - skill_names
    if missing:
        issues.append(
            Issue(
                "error",
                "skills-manifest.json",
                f"missing skills: {', '.join(sorted(missing))}",
            )
        )
    if extra:
        issues.append(
            Issue(
                "error",
                "skills-manifest.json",
                f"unknown skills: {', '.join(sorted(extra))}",
            )
        )


def validate_trigger_cases(
    root: Path, skill_names: set[str], issues: list[Issue]
) -> None:
    eval_path = root / "evals" / "trigger-cases.json"
    payload = load_json(eval_path, root, issues)
    if not isinstance(payload, dict):
        return

    cases = payload.get("cases")
    if not isinstance(cases, list):
        issues.append(
            Issue("error", "evals/trigger-cases.json", "cases must be a list")
        )
        return

    seen: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            issues.append(
                Issue(
                    "error",
                    "evals/trigger-cases.json",
                    f"cases[{index}] must be an object",
                )
            )
            continue
        skill = case.get("skill")
        positive = case.get("should_trigger")
        negative = case.get("should_not_trigger")

        if not isinstance(skill, str):
            issues.append(
                Issue(
                    "error",
                    "evals/trigger-cases.json",
                    f"cases[{index}].skill must be a string",
                )
            )
            continue
        seen.add(skill)

        if not isinstance(positive, list) or len(positive) < 2:
            issues.append(
                Issue(
                    "error",
                    "evals/trigger-cases.json",
                    f"{skill} needs at least two should_trigger examples",
                )
            )
        if not isinstance(negative, list) or len(negative) < 2:
            issues.append(
                Issue(
                    "error",
                    "evals/trigger-cases.json",
                    f"{skill} needs at least two should_not_trigger examples",
                )
            )

    missing = skill_names - seen
    extra = seen - skill_names
    if missing:
        issues.append(
            Issue(
                "error",
                "evals/trigger-cases.json",
                f"missing skills: {', '.join(sorted(missing))}",
            )
        )
    if extra:
        issues.append(
            Issue(
                "error",
                "evals/trigger-cases.json",
                f"unknown skills: {', '.join(sorted(extra))}",
            )
        )


def validate_repository(root: Path) -> list[Issue]:
    root = root.resolve()
    issues: list[Issue] = []
    skill_dirs = sorted(
        path
        for path in root.glob("py-*")
        if path.is_dir() and (path / "SKILL.md").is_file()
    )
    if not skill_dirs:
        return [Issue("error", ".", "no py-*/SKILL.md directories found")]

    for skill_dir in skill_dirs:
        issues.extend(validate_skill(skill_dir, root))

    skill_names = {path.name for path in skill_dirs}
    validate_manifest(root, skill_names, issues)
    validate_trigger_cases(root, skill_names, issues)
    return sorted(
        issues, key=lambda item: (item.path, item.level, item.message)
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (default: inferred from this script)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat warnings as failures",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="print machine-readable JSON",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    issues = validate_repository(args.root)

    if args.json_output:
        print(
            json.dumps(
                [asdict(issue) for issue in issues],
                ensure_ascii=False,
                indent=2,
            )
        )
    elif issues:
        for issue in issues:
            print(f"{issue.level.upper():7} {issue.path}: {issue.message}")
    else:
        print("OK: all skills passed repository validation")

    errors = sum(issue.level == "error" for issue in issues)
    warnings = sum(issue.level == "warning" for issue in issues)
    if not args.json_output:
        print(f"Summary: {errors} error(s), {warnings} warning(s)")

    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
