from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("validate_plugin_test_module", ROOT / "scripts" / "validate_plugin.py")
INSTALLER = load_module("install_codex_test_module", ROOT / "scripts" / "install_codex.py")
UNINSTALLER = load_module("uninstall_codex_test_module", ROOT / "scripts" / "uninstall_codex.py")


class PluginFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        skill = root / "py-example"
        (skill / "references").mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: py-example\ndescription: Example skill used by tests.\n---\n", encoding="utf-8")
        (skill / "references" / "examples.md").write_text("# Examples\n", encoding="utf-8")

        destination = root / "skills" / "py-example"
        shutil.copytree(skill, destination)

        (root / ".codex-plugin").mkdir(parents=True)
        (root / ".codex-plugin" / "plugin.json").write_text(
            json.dumps(
                {
                    "name": "python-engineering-skills",
                    "version": "1.0.0",
                    "description": "Test plugin",
                    "skills": "./skills/",
                }
            ),
            encoding="utf-8",
        )

        (root / ".agents" / "plugins").mkdir(parents=True)
        (root / ".agents" / "plugins" / "marketplace.json").write_text(
            json.dumps(
                {
                    "name": "test",
                    "plugins": [
                        {
                            "name": "python-engineering-skills",
                            "source": {"source": "local", "path": "./"},
                            "policy": {
                                "installation": "AVAILABLE",
                                "authentication": "ON_INSTALL",
                            },
                            "category": "Developer Tools",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        (root / "skills-manifest.json").write_text(
            json.dumps({"skills": [{"name": "py-example"}]}),
            encoding="utf-8",
        )

        scripts = root / "scripts"
        scripts.mkdir()
        for name in ("install_codex.py", "uninstall_codex.py", "install_codex.sh", "install_codex.ps1"):
            (scripts / name).write_text("# test\n", encoding="utf-8")


class ValidatePluginTests(unittest.TestCase):
    def test_valid_fixture_has_no_issues(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            PluginFixture(root)
            self.assertEqual(VALIDATOR.validate_repository(root), [])

    def test_skill_drift_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            PluginFixture(root)
            (root / "skills" / "py-example" / "SKILL.md").write_text("changed\n", encoding="utf-8")
            messages = [item.message for item in VALIDATOR.validate_repository(root)]
            self.assertTrue(any("mirror differs" in message for message in messages))

    def test_manifest_path_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            PluginFixture(root)
            path = root / ".codex-plugin" / "plugin.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["skills"] = "./../outside"
            path.write_text(json.dumps(payload), encoding="utf-8")
            messages = [item.message for item in VALIDATOR.validate_repository(root)]
            self.assertTrue(any("escapes the repository root" in message for message in messages))


class InstallerTests(unittest.TestCase):
    def test_plugin_install_preserves_other_marketplace_entries_and_replaces_old_copy(self) -> None:
        with tempfile.TemporaryDirectory() as source_temp, tempfile.TemporaryDirectory() as home_temp:
            source = Path(source_temp)
            PluginFixture(source)
            home = Path(home_temp)
            marketplace = home / ".agents" / "plugins" / "marketplace.json"
            marketplace.parent.mkdir(parents=True)
            marketplace.write_text(
                json.dumps(
                    {
                        "name": "existing",
                        "plugins": [
                            {
                                "name": "other-plugin",
                                "source": {"source": "local", "path": "./other-plugin"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            old = home / ".codex" / "plugins" / "python-engineering-skills"
            old.mkdir(parents=True)
            (old / "old.txt").write_text("old", encoding="utf-8")

            result = INSTALLER.main(
                [
                    "--mode", "plugin",
                    "--scope", "user",
                    "--home", str(home),
                    "--source-root", str(source),
                ]
            )
            self.assertEqual(result, 0)
            self.assertFalse((old / "old.txt").exists())
            self.assertTrue((old / ".codex-plugin" / "plugin.json").is_file())

            payload = json.loads(marketplace.read_text(encoding="utf-8"))
            names = {item["name"] for item in payload["plugins"]}
            self.assertEqual(names, {"other-plugin", "python-engineering-skills"})

    def test_uninstall_preserves_unrelated_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as source_temp, tempfile.TemporaryDirectory() as home_temp:
            source = Path(source_temp)
            PluginFixture(source)
            home = Path(home_temp)
            INSTALLER.main(
                [
                    "--mode", "plugin",
                    "--scope", "user",
                    "--home", str(home),
                    "--source-root", str(source),
                ]
            )
            marketplace = home / ".agents" / "plugins" / "marketplace.json"
            payload = json.loads(marketplace.read_text(encoding="utf-8"))
            payload["plugins"].append(
                {
                    "name": "other-plugin",
                    "source": {"source": "local", "path": "./other-plugin"},
                }
            )
            marketplace.write_text(json.dumps(payload), encoding="utf-8")

            result = UNINSTALLER.main(
                [
                    "--mode", "plugin",
                    "--scope", "user",
                    "--home", str(home),
                    "--source-root", str(source),
                ]
            )
            self.assertEqual(result, 0)
            self.assertFalse((home / ".codex" / "plugins" / "python-engineering-skills").exists())
            payload = json.loads(marketplace.read_text(encoding="utf-8"))
            self.assertEqual([item["name"] for item in payload["plugins"]], ["other-plugin"])


if __name__ == "__main__":
    unittest.main()
