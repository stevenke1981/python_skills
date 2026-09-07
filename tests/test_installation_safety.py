"""Regression tests exercise real filesystem operations and extracted ZIPs."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import codex_fs as fs
import install_codex as install
import package_plugin as package
import sync_plugin_skills as sync
import uninstall_codex as uninstall


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts} if root.exists() else {}


def fixture(root: Path) -> None:
    root.mkdir(parents=True)
    for name in ("py-example", "py-extra"):
        skill = root / name
        (skill / "references").mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: A test skill.\n---\n", encoding="utf-8")
        (skill / "references/examples.md").write_text("original\n", encoding="utf-8")
        shutil.copytree(skill, root / "skills" / name)
    (root / "skills-manifest.json").write_bytes(fs.json_bytes({"skills": [
        {"name": "py-example"}, {"name": "py-extra"}]}))
    (root / ".codex-plugin").mkdir()
    (root / ".codex-plugin/plugin.json").write_bytes(fs.json_bytes({
        "name": fs.PLUGIN_NAME, "version": "1.0.1", "skills": "./skills/", "description": "Fixture"}))
    (root / ".agents/plugins").mkdir(parents=True)
    (root / ".agents/plugins/marketplace.json").write_bytes(fs.json_bytes({
        "name": "test", "plugins": [install.marketplace_entry("./")]}))
    (root / "scripts").mkdir()
    for name in install.RUNTIME_FILES:
        shutil.copy2(ROOT / "scripts" / name, root / "scripts" / name)
    for name in ("README.md", "CODEX_PLUGIN.md"):
        (root / name).write_text("# Fixture\n", encoding="utf-8")


class InstallationSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.source, self.home = self.base / "來源 source", self.base / "使用者 home"
        fixture(self.source)

    def run_cli(self, module, *extra: str, mode: str = "skills", scope: str = "user") -> int:
        args = ["--source-root", str(self.source), "--home", str(self.home),
                "--mode", mode, "--scope", scope, *extra]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return module.main(args)

    def targets(self, mode: str = "skills") -> list[Path]:
        if mode == "plugin":
            return [self.home / ".codex/plugins" / fs.PLUGIN_NAME]
        return [self.home / ".agents/skills" / name for name in ("py-example", "py-extra")]

    def link(self, target: Path, link: Path, is_dir: bool = False) -> None:
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(target, target_is_directory=is_dir)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Platform does not permit symlink creation: {exc}")

    def test_user_install_upgrade_uninstall_both_modes(self) -> None:
        for mode in ("skills", "plugin"):
            with self.subTest(mode=mode):
                self.assertEqual(self.run_cli(install, mode=mode), 0)
                for target in self.targets(mode):
                    self.assertTrue((target / fs.RECEIPT).is_file())
                self.assertEqual(self.run_cli(install, mode=mode), 0)
                self.assertEqual(self.run_cli(uninstall, mode=mode), 0)
                self.assertEqual(self.run_cli(uninstall, mode=mode), 0)
                self.assertTrue(all(not p.exists() for p in self.targets(mode)))

    def test_repo_install_and_remove_both_modes(self) -> None:
        target = self.base / "目標 repo"
        for mode in ("skills", "plugin"):
            with self.subTest(mode=mode):
                self.assertEqual(self.run_cli(install, "--repo-root", str(target), mode=mode, scope="repo"), 0)
                self.assertEqual(self.run_cli(uninstall, "--repo-root", str(target), mode=mode, scope="repo"), 0)

    def test_dry_run_never_creates_target_directories(self) -> None:
        for mode in ("skills", "plugin"):
            self.assertEqual(self.run_cli(install, "--dry-run", mode=mode), 0)
            self.assertEqual(self.run_cli(uninstall, "--dry-run", mode=mode), 0)
            self.assertFalse(self.home.exists())

    def test_missing_repo_root_is_clean_error(self) -> None:
        for module in (install, uninstall):
            self.assertEqual(self.run_cli(module, scope="repo"), 1)
        self.assertFalse(self.home.exists())

    def test_unmanaged_files_require_explicit_force(self) -> None:
        target = self.targets()[0]
        target.mkdir(parents=True)
        (target / "notes.txt").write_text("my notes", encoding="utf-8")
        before = snapshot(self.home)
        self.assertEqual(self.run_cli(install), 1)
        self.assertEqual(self.run_cli(uninstall), 1)
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.run_cli(install, "--force"), 0)

    def test_modified_files_require_force_for_install_and_uninstall(self) -> None:
        for mode in ("skills", "plugin"):
            with self.subTest(mode=mode):
                self.assertEqual(self.run_cli(install, mode=mode), 0)
                target = self.targets(mode)[0]
                (target / "personal-notes.md").write_text("keep this", encoding="utf-8")
                before = snapshot(self.home)
                self.assertEqual(self.run_cli(install, mode=mode), 1)
                self.assertEqual(self.run_cli(uninstall, mode=mode), 1)
                self.assertEqual(snapshot(self.home), before)
                self.assertEqual(self.run_cli(uninstall, "--force", mode=mode), 0)

    def test_unrelated_skills_and_marketplace_entries_are_preserved(self) -> None:
        unrelated = self.home / ".agents/skills/other-skill/SKILL.md"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("keep", encoding="utf-8")
        marketplace = self.home / ".agents/plugins/marketplace.json"
        marketplace.parent.mkdir(parents=True)
        marketplace.write_bytes(b'\xef\xbb\xbf' + fs.json_bytes({"name": "custom", "setting": 42,
            "plugins": [{"name": "other-plugin", "custom": True}]}))
        for mode in ("plugin", "skills"):
            self.assertEqual(self.run_cli(install, mode=mode), 0)
            self.assertEqual(self.run_cli(uninstall, mode=mode), 0)
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep")
        self.assertEqual(fs.json_object(marketplace), {"name": "custom", "setting": 42,
            "interface": {"displayName": "StevenKe Python Plugins"},
            "plugins": [{"name": "other-plugin", "custom": True}]})

    def test_invalid_marketplace_never_removes_old_install(self) -> None:
        self.assertEqual(self.run_cli(install, mode="plugin"), 0)
        marketplace = self.home / ".agents/plugins/marketplace.json"
        for content in (b"{bad", b"[]", b'{"plugins":null}', b"\xff"):
            with self.subTest(content=content):
                marketplace.write_bytes(content)
                before = snapshot(self.home)
                for module in (install, uninstall):
                    self.assertEqual(self.run_cli(module, mode="plugin"), 1)
                    self.assertEqual(self.run_cli(module, "--dry-run", mode="plugin"), 1)
                self.assertEqual(snapshot(self.home), before)

    def test_invalid_and_traversal_names_cannot_delete_anything(self) -> None:
        marker = self.base / "outside.txt"
        marker.write_text("keep", encoding="utf-8")
        for name in ("../outside", "..", "/etc", "C:\\temp", "py-a/b", "py-a\\b", "py--bad", "py-" + "x" * 64, None):
            with self.subTest(name=name):
                (self.source / "skills-manifest.json").write_bytes(fs.json_bytes({"skills": [{"name": name}]}))
                self.assertEqual(self.run_cli(install), 1)
                self.assertEqual(self.run_cli(uninstall, "--force"), 1)
                self.assertFalse(self.home.exists())
                self.assertTrue(marker.exists())

    def test_bad_manifest_shapes_fail_closed(self) -> None:
        for payload in ([], None, {}, {"skills": []}, {"skills": "py-example"},
                        {"skills": [{"name": "py-example"}, {"name": "py-example"}]}):
            with self.subTest(payload=payload):
                (self.source / "skills-manifest.json").write_text(json.dumps(payload), encoding="utf-8")
                self.assertEqual(self.run_cli(install), 1)
                self.assertEqual(self.run_cli(uninstall), 1)

    def test_missing_source_prevents_partial_install(self) -> None:
        (self.source / "skills/py-extra/SKILL.md").unlink()
        self.assertEqual(self.run_cli(install), 1)
        self.assertFalse(self.home.exists())

    def test_self_install_is_rejected(self) -> None:
        before = snapshot(self.source)
        self.assertEqual(self.run_cli(install, "--repo-root", str(self.source), scope="repo"), 1)
        self.assertEqual(snapshot(self.source), before)

    def test_copy_failure_preserves_all_old_skills(self) -> None:
        self.assertEqual(self.run_cli(install), 0)
        before = snapshot(self.home)
        with patch.object(fs.shutil, "copytree", side_effect=OSError("injected copy failure")):
            self.assertEqual(self.run_cli(install), 1)
        self.assertEqual(snapshot(self.home), before)

    def test_later_promotion_failure_rolls_back_all_skills(self) -> None:
        self.assertEqual(self.run_cli(install), 0)
        before = snapshot(self.home)
        (self.source / "skills/py-example/SKILL.md").write_text("new content", encoding="utf-8")
        original = os.replace
        def fail_second(src, dst):
            if Path(src).name == "new" and Path(dst) == self.targets()[1]:
                raise OSError("injected second promotion failure")
            return original(src, dst)
        with patch.object(fs.os, "replace", side_effect=fail_second):
            self.assertEqual(self.run_cli(install), 1)
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(list(self.home.rglob(".python-skills-txn-*")), [])

    def test_marketplace_write_failure_rolls_back_plugin_install_and_remove(self) -> None:
        self.assertEqual(self.run_cli(install, mode="plugin"), 0)
        before = snapshot(self.home)
        original = os.replace
        def fail_config(src, dst):
            if Path(src).name == "new" and Path(dst).name == "marketplace.json":
                raise OSError("injected configuration failure")
            return original(src, dst)
        for module in (install, uninstall):
            with patch.object(fs.os, "replace", side_effect=fail_config):
                self.assertEqual(self.run_cli(module, mode="plugin"), 1)
            self.assertEqual(snapshot(self.home), before)

    def test_source_symlink_is_rejected(self) -> None:
        outside = self.base / "private.txt"
        outside.write_text("private", encoding="utf-8")
        self.link(outside, self.source / "skills/py-example/private.txt")
        self.assertEqual(self.run_cli(install), 1)
        self.assertFalse(self.home.exists())

    def test_target_parent_symlink_is_rejected(self) -> None:
        outside = self.base / "outside"
        outside.mkdir()
        self.link(outside, self.home / ".agents", is_dir=True)
        self.assertEqual(self.run_cli(install, "--force"), 1)
        self.assertEqual(self.run_cli(uninstall, "--force"), 1)
        self.assertEqual(snapshot(outside), {})

    def test_dangling_target_symlink_is_rejected(self) -> None:
        self.link(self.base / "does-not-exist", self.targets()[0], is_dir=True)
        self.assertEqual(self.run_cli(install, "--force"), 1)
        self.assertEqual(self.run_cli(uninstall, "--force"), 1)

    @unittest.skipUnless(os.name == "nt", "Windows-only scope guard")
    def test_admin_scope_is_rejected_on_windows(self) -> None:
        for module in (install, uninstall):
            self.assertEqual(self.run_cli(module, scope="admin"), 1)

    def test_sync_empty_sources_does_not_clean_mirror(self) -> None:
        before = snapshot(self.source / "skills")
        for path in self.source.glob("py-*"):
            shutil.rmtree(path)
        with self.assertRaises(ValueError):
            sync.synchronize(self.source)
        self.assertEqual(snapshot(self.source / "skills"), before)

    def test_sync_missing_skill_file_does_not_clean_mirror(self) -> None:
        before = snapshot(self.source / "skills")
        (self.source / "py-extra/SKILL.md").unlink()
        with self.assertRaises(ValueError):
            sync.synchronize(self.source)
        self.assertEqual(snapshot(self.source / "skills"), before)

    def test_sync_updates_changed_files_without_rewriting_unchanged_files(self) -> None:
        stable = self.source / "skills/py-extra/SKILL.md"
        mtime = stable.stat().st_mtime_ns
        (self.source / "py-example/SKILL.md").write_text("changed", encoding="utf-8")
        self.assertTrue(sync.check_sync(self.source))
        sync.synchronize(self.source)
        self.assertEqual(sync.check_sync(self.source), [])
        self.assertEqual(stable.stat().st_mtime_ns, mtime)

    def test_sync_preserves_unrelated_entries(self) -> None:
        custom = self.source / "skills/personal-notes"
        custom.mkdir()
        (custom / "important.txt").write_text("keep", encoding="utf-8")
        before = snapshot(self.source / "skills")
        with self.assertRaises(ValueError):
            sync.synchronize(self.source)
        self.assertEqual(snapshot(self.source / "skills"), before)

    def test_zip_is_reproducible_and_contains_runtime_dependencies(self) -> None:
        a, b = self.base / "a.zip", self.base / "b.zip"
        cache = self.source / "skills/py-example/__pycache__"
        cache.mkdir()
        (cache / "junk.pyc").write_bytes(b"junk")
        package.write_zip(self.source, a)
        os.utime(self.source / "skills/py-example/SKILL.md", (1000000000, 1000000000))
        package.write_zip(self.source, b)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        with zipfile.ZipFile(a) as archive:
            self.assertIn("skills-manifest.json", archive.namelist())
            self.assertIn("scripts/codex_fs.py", archive.namelist())
            self.assertTrue(all("__pycache__" not in n for n in archive.namelist()))
            self.assertTrue(all(info.create_system == 3 for info in archive.infolist()))

    def test_zip_missing_runtime_file_keeps_previous_artifact(self) -> None:
        output = self.base / "existing.zip"
        output.write_bytes(b"previous artifact")
        (self.source / "scripts/codex_fs.py").unlink()
        with self.assertRaises(ValueError):
            package.write_zip(self.source, output)
        self.assertEqual(output.read_bytes(), b"previous artifact")

    def test_zip_output_cannot_overwrite_source(self) -> None:
        source = self.source / "README.md"
        before = source.read_bytes()
        with self.assertRaises(ValueError):
            package.write_zip(self.source, source)
        self.assertEqual(source.read_bytes(), before)

    def test_zip_rejects_symlink_sources(self) -> None:
        outside = self.base / "secret.txt"
        outside.write_text("secret", encoding="utf-8")
        self.link(outside, self.source / "skills/py-example/secret.txt")
        with self.assertRaises(ValueError):
            package.write_zip(self.source, self.base / "bad.zip")

    def test_extracted_zip_install_and_uninstall_without_source_checkout(self) -> None:
        archive = self.base / "bundle.zip"
        package.write_zip(self.source, archive)
        extracted = self.base / "解壓 package"
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(extracted)
        shutil.rmtree(self.source)  # Missing manifest bug used to hide behind the checkout.
        for mode in ("plugin", "skills"):
            for script in ("install_codex.py", "uninstall_codex.py"):
                command = [sys.executable, str(extracted / "scripts" / script),
                           "--mode", mode, "--home", str(self.home)]
                result = subprocess.run(command, cwd=self.base, capture_output=True,
                                        text=True, encoding="utf-8", timeout=30,
                                        env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
