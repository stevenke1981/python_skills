from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_skills.py"


def load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("validate_skills", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


validator = load_validator()


class ValidatorTests(unittest.TestCase):
    def make_repo(self, root: Path, skill_text: str) -> None:
        skill_dir = root / "py-example"
        references = skill_dir / "references"
        references.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(skill_text, encoding="utf-8")
        for filename in ("examples.md", "cheatsheet.md", "pitfalls.md"):
            (references / filename).write_text("# Reference\n", encoding="utf-8")

        (root / "skills-manifest.json").write_text(
            json.dumps({"skills": [{"name": "py-example"}]}),
            encoding="utf-8",
        )
        eval_dir = root / "evals"
        eval_dir.mkdir()
        (eval_dir / "trigger-cases.json").write_text(
            json.dumps(
                {
                    "cases": [
                        {
                            "skill": "py-example",
                            "should_trigger": ["positive one", "positive two"],
                            "should_not_trigger": ["negative one", "negative two"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    @staticmethod
    def valid_skill() -> str:
        return textwrap.dedent(
            """
            ---
            name: py-example
            description: >
              Example validator skill for repository tests. Use when checking skill files.
            compatibility: Agent Skills-compatible.
            metadata:
              version: "2.0.0"
            ---

            # Example

            ## 執行流程

            1. Validate the repository.

            ## 交付標準

            - Return clear errors.

            ## 延伸閱讀

            - [Examples](references/examples.md)
            - [Cheatsheet](references/cheatsheet.md)
            - [Pitfalls](references/pitfalls.md)

            ## 版本相容性

            Python 3.11+.
            """
        ).lstrip()

    def test_valid_repository_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.make_repo(root, self.valid_skill())
            self.assertEqual(validator.validate_repository(root), [])

    def test_name_must_match_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content = self.valid_skill().replace(
                "name: py-example", "name: another-skill", 1
            )
            self.make_repo(root, content)
            issues = validator.validate_repository(root)
            self.assertTrue(
                any("must match parent directory" in issue.message for issue in issues)
            )

    def test_missing_required_heading_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content = self.valid_skill().replace("## 交付標準", "## Output")
            self.make_repo(root, content)
            issues = validator.validate_repository(root)
            self.assertTrue(
                any("missing required heading" in issue.message for issue in issues)
            )

    def test_broken_relative_link_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content = self.valid_skill().replace(
                "references/examples.md", "references/missing.md"
            )
            self.make_repo(root, content)
            issues = validator.validate_repository(root)
            self.assertTrue(any("broken relative link" in issue.message for issue in issues))

    def test_code_that_resembles_markdown_links_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            code = textwrap.dedent(
                r'''
                ```python
                pattern = r"^[^\\/](?!.*\.\.).*$"

                def first[T](items: list[T]) -> T:
                    return items[0]
                ```
                '''
            ).strip()
            content = self.valid_skill().replace(
                "1. Validate the repository.",
                code,
            )
            self.make_repo(root, content)
            self.assertEqual(validator.validate_repository(root), [])

    def test_folded_description_is_parsed(self) -> None:
        fields, _ = validator.parse_frontmatter(
            self.valid_skill(), Path("py-example/SKILL.md")
        )
        self.assertIn("Example validator skill", fields["description"])
        self.assertIn("checking skill files", fields["description"])


if __name__ == "__main__":
    unittest.main()
