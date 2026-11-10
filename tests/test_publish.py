"""Tests for scripts/publish_github.py. Nothing here talks to GitHub: only pure helpers and the dry run."""
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import publish_github as pg  # noqa: E402

TOKEN = pg.OWNER_TOKEN


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in pg.project_files(root):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


class ReplaceOwnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        (self.root / "scripts").mkdir()
        (self.root / "dist").mkdir()
        (self.root / "docs.md").write_bytes(f"clone https://github.com/{TOKEN}/diavlo-mind\r\nadd {TOKEN}/diavlo-mind\r\n".encode())
        (self.root / "plain.txt").write_text("nothing to replace here\n", encoding="utf-8")
        (self.root / "scripts" / "validate.py").write_text(f'OWNER_TOKEN = "{TOKEN}"\n', encoding="utf-8")
        (self.root / "image.png").write_bytes(b"\x89PNG\0\0" + TOKEN.encode())
        (self.root / "dist" / "old.md").write_text(f"{TOKEN}\n", encoding="utf-8")

    def test_replaces_text_files_and_keeps_line_endings(self):
        changed = pg.replace_owner(self.root, "octo-test")
        self.assertEqual(changed, ["docs.md"])
        self.assertEqual((self.root / "docs.md").read_bytes(),
                         b"clone https://github.com/octo-test/diavlo-mind\r\nadd octo-test/diavlo-mind\r\n")

    def test_leaves_binary_files_build_output_and_the_scripts_that_need_the_token(self):
        pg.replace_owner(self.root, "octo-test")
        self.assertIn(TOKEN.encode(), (self.root / "image.png").read_bytes())
        self.assertIn(TOKEN, (self.root / "scripts" / "validate.py").read_text(encoding="utf-8"))
        self.assertIn(TOKEN, (self.root / "dist" / "old.md").read_text(encoding="utf-8"))

    def test_write_false_reports_without_changing(self):
        before = (self.root / "docs.md").read_bytes()
        self.assertEqual(pg.replace_owner(self.root, "octo-test", write=False), ["docs.md"])
        self.assertEqual((self.root / "docs.md").read_bytes(), before)

    def test_other_repository_name_changes_urls_only(self):
        (self.root / "docs.md").write_text(f"git clone https://github.com/{TOKEN}/diavlo-mind ~/.claude/skills/diavlo-mind\n", encoding="utf-8")
        pg.replace_owner(self.root, "octo-test", repo="mind-fork")
        self.assertEqual((self.root / "docs.md").read_text(encoding="utf-8"),
                         "git clone https://github.com/octo-test/mind-fork ~/.claude/skills/diavlo-mind\n")

    def test_previous_owner_is_replaced_when_republishing(self):
        pg.replace_owner(self.root, "first-owner")
        changed = pg.replace_owner(self.root, "second-owner", previous_owner="first-owner")
        self.assertEqual(changed, ["docs.md"])
        self.assertNotIn("first-owner", (self.root / "docs.md").read_text(encoding="utf-8"))

    def test_written_owner_is_read_from_the_plugin_manifest(self):
        manifest = self.root / ".claude-plugin"
        manifest.mkdir()
        (manifest / "plugin.json").write_text('{"repository": "https://github.com/' + TOKEN + '/diavlo-mind"}', encoding="utf-8")
        self.assertIsNone(pg.written_owner(self.root))
        pg.replace_owner(self.root, "first-owner")
        self.assertEqual(pg.written_owner(self.root), "first-owner")
        pg.replace_owner(self.root, "second-owner", previous_owner=pg.written_owner(self.root))
        self.assertEqual(pg.written_owner(self.root), "second-owner")
        self.assertNotIn("first-owner", (self.root / "docs.md").read_text(encoding="utf-8"))

    def test_second_run_changes_nothing(self):
        pg.replace_owner(self.root, "octo-test")
        self.assertEqual(pg.replace_owner(self.root, "octo-test"), [])


class HelperTests(unittest.TestCase):
    def test_changelog_section_returns_one_version(self):
        text = "# Changelog\n\n## [1.1.0] — 2027-01-01\n\nSecond.\n\n## [1.0.0] — 2026-11-10\n\nFirst.\n\n### Added\n\n- thing\n"
        self.assertEqual(pg.changelog_section(text, "1.1.0"), "Second.")
        self.assertEqual(pg.changelog_section(text, "1.0.0"), "First.\n\n### Added\n\n- thing")
        self.assertEqual(pg.changelog_section(text, "9.9.9"), "")

    def test_repository_changelog_has_the_current_version(self):
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertTrue(pg.changelog_section((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), version))

    def test_metadata_file_respects_github_limits(self):
        meta = pg.load_metadata(ROOT)
        self.assertLessEqual(len(meta["topics"]), 20)
        self.assertEqual(len(meta["topics"]), len(set(meta["topics"])))
        self.assertLessEqual(len(meta["description"]), 350)
        self.assertTrue((ROOT / meta["social_preview"]).is_file())

    def test_release_notes_contain_install_command_and_changes(self):
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        notes = pg.release_notes(ROOT, version, "octo-test", "diavlo-mind")
        self.assertIn("git clone https://github.com/octo-test/diavlo-mind", notes)
        self.assertIn("### Added", notes)

    def test_noreply_identity_never_uses_a_private_address(self):
        self.assertEqual(pg.noreply_identity("octo-test", "12345"), ("octo-test", "12345+octo-test@users.noreply.github.com"))

    def test_parse_steps_orders_and_rejects(self):
        self.assertEqual(pg.parse_steps(None), pg.STEPS)
        self.assertEqual(pg.parse_steps("release, push"), ["push", "release"])
        with self.assertRaises(pg.PublishError):
            pg.parse_steps("push,deploy")


class DryRunTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / "publish_github.py"), *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", cwd=str(ROOT))

    def test_dry_run_plans_every_step_and_changes_nothing(self):
        before = tree_digest(ROOT)
        done = self.run_cli("--dry-run", "--owner", "octo-test")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(tree_digest(ROOT), before)
        for step in pg.STEPS:
            self.assertIn(f"[{step}]", done.stdout)
        self.assertIn("gh repo create octo-test/diavlo-mind --public", done.stdout)
        self.assertIn("git push -u origin main", done.stdout)
        self.assertIn("users.noreply.github.com", done.stdout)
        self.assertIn("--add-topic agent-skills", done.stdout)
        self.assertIn("gh release create v", done.stdout)
        self.assertIn("nothing was changed", done.stdout)

    def test_private_flag_and_step_subset(self):
        done = self.run_cli("--dry-run", "--owner", "octo-test", "--private", "--steps", "create")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("--private", done.stdout)
        self.assertNotIn("[push]", done.stdout)

    def test_invalid_owner_and_step_are_refused(self):
        self.assertEqual(self.run_cli("--dry-run", "--owner", "bad name!").returncode, 1)
        self.assertEqual(self.run_cli("--dry-run", "--owner", "octo-test", "--steps", "deploy").returncode, 1)


if __name__ == "__main__":
    unittest.main()
