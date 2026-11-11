"""Tests for scripts/install_all.py and install-all.bat: every AI tool at once, with the default-use rule."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import install_all  # noqa: E402

PY = sys.executable
ALL = "claude-code,codex,gemini-cli,antigravity"
USER_TEXT = "# Mis reglas\nResponde en español.\n"


class BlockTests(unittest.TestCase):
    """The text handling, with no files."""

    def block(self, key="claude-code", lang="en"):
        host = next(h for h in install_all.HOSTS if h.key == key)
        return install_all.render_block(host, lang)

    def test_block_is_added_after_existing_text_and_removed_to_get_it_back(self):
        added, status = install_all.apply_block(USER_TEXT, self.block())
        self.assertEqual(status, "added")
        self.assertTrue(added.startswith(USER_TEXT.rstrip("\n")))
        self.assertEqual(added.count(install_all.MARK_BEGIN_PREFIX), 1)
        restored, removed = install_all.remove_block(added)
        self.assertTrue(removed)
        self.assertEqual(restored, USER_TEXT)

    def test_applying_twice_changes_nothing(self):
        once, _ = install_all.apply_block(USER_TEXT, self.block())
        twice, status = install_all.apply_block(once, self.block())
        self.assertEqual((twice, status), (once, "unchanged"))

    def test_an_older_block_is_replaced_in_place_and_the_text_around_it_stays(self):
        old = install_all.MARK_BEGIN_PREFIX + " (older wording) -->\nold rule\n" + install_all.MARK_END
        text = "before\n\n" + old + "\n\nafter\n"
        new, status = install_all.apply_block(text, self.block())
        self.assertEqual(status, "updated")
        self.assertTrue(new.startswith("before\n\n" + install_all.MARK_BEGIN))
        self.assertTrue(new.endswith("\n\nafter\n"))
        self.assertNotIn("old rule", new)

    def test_damaged_marks_are_refused_not_guessed(self):
        for text in (install_all.MARK_BEGIN_PREFIX + " -->\nno end\n",
                     install_all.MARK_END + "\nend first\n" + install_all.MARK_BEGIN_PREFIX + " -->\n",
                     self.block() + "\n" + self.block() + "\n"):
            with self.assertRaises(install_all.MarkError):
                install_all.apply_block(text, self.block())
            with self.assertRaises(install_all.MarkError):
                install_all.remove_block(text)

    def test_each_tool_gets_its_own_way_to_call_the_skill(self):
        self.assertIn("/diavlo-mind", self.block("claude-code"))
        self.assertIn("$diavlo-mind", self.block("codex"))
        self.assertIn("skills mechanism", self.block("gemini-cli"))
        self.assertIn("método de trabajo", self.block("claude-code", "es"))

    def test_language_follows_the_environment(self):
        saved = {name: os.environ.get(name) for name in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG")}
        self.addCleanup(lambda: [os.environ.__setitem__(k, v) if v is not None else os.environ.pop(k, None) for k, v in saved.items()])
        for name in saved:
            os.environ.pop(name, None)
        os.environ["LANG"] = "es_ES.UTF-8"
        self.assertEqual(install_all.detect_lang(), "es")
        os.environ["LANG"] = "en_US.UTF-8"
        self.assertEqual(install_all.detect_lang(), "en")


class FileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        host = next(h for h in install_all.HOSTS if h.key == "claude-code")
        self.block = install_all.render_block(host, "en")

    def test_new_file_existing_file_and_backup(self):
        path = self.dir / "sub" / "CLAUDE.md"
        self.assertEqual(install_all.update_rule(path, self.block, False)[0], "created")
        self.assertEqual(list(path.parent.glob("*.bak-*")), [])
        path.write_bytes(path.read_bytes() + b"\nmine\n")
        status, backup = install_all.update_rule(path, self.block, False)
        self.assertEqual(status, "unchanged")
        self.assertEqual(backup, "")
        path.write_text("hello\n", encoding="utf-8")
        status, backup = install_all.update_rule(path, self.block, False)
        self.assertEqual(status, "added")
        self.assertEqual(Path(backup).read_text(encoding="utf-8"), "hello\n")

    def test_crlf_and_bom_are_kept(self):
        path = self.dir / "AGENTS.md"
        path.write_bytes(install_all.BOM + "línea uno\r\nlínea dos\r\n".encode("utf-8"))
        install_all.update_rule(path, self.block, False)
        data = path.read_bytes()
        self.assertTrue(data.startswith(install_all.BOM))
        self.assertEqual(data.count(b"\n"), data.count(b"\r\n"), "every line ending must stay CRLF")
        self.assertIn("línea dos".encode("utf-8"), data)
        install_all.update_rule(path, None, False)
        self.assertEqual(path.read_bytes(), install_all.BOM + "línea uno\r\nlínea dos\r\n".encode("utf-8"))

    def test_a_utf16_file_is_left_untouched(self):
        path = self.dir / "GEMINI.md"
        original = "hola\n".encode("utf-16")      # what PowerShell's > writes
        path.write_bytes(original)
        self.assertEqual(install_all.update_rule(path, self.block, False)[0], "encoding")
        self.assertEqual(path.read_bytes(), original)

    def test_dry_run_writes_nothing(self):
        path = self.dir / "CLAUDE.md"
        path.write_text("keep\n", encoding="utf-8")
        status, _ = install_all.update_rule(path, self.block, True)
        self.assertEqual(status, "added")
        self.assertEqual(path.read_text(encoding="utf-8"), "keep\n")
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ["CLAUDE.md"])

    def test_removing_the_only_content_deletes_the_file(self):
        path = self.dir / "AGENTS.md"
        install_all.update_rule(path, self.block, False)
        self.assertEqual(install_all.update_rule(path, None, False)[0], "deleted")
        self.assertFalse(path.exists())
        self.assertEqual(install_all.update_rule(path, None, False)[0], "absent")


class CommandTests(unittest.TestCase):
    """The whole script, run as a user would, with a throwaway home folder."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.empty_path = Path(self.tmp.name) / "no-tools"
        self.empty_path.mkdir()

    def run_all(self, *args, expect=0):
        env = dict(os.environ, DM_HOME=str(self.home), PATH=str(self.empty_path), PYTHONUTF8="1")
        for name in ("CODEX_HOME", "LC_ALL", "LC_MESSAGES", "LANGUAGE"):
            env.pop(name, None)
        env["LANG"] = "en_US.UTF-8"
        out = subprocess.run([PY, str(SCRIPTS / "install_all.py"), *args], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", env=env)
        self.assertEqual(out.returncode, expect, out.stdout + out.stderr)
        return out.stdout

    def rules(self):
        return {
            "claude": self.home / ".claude" / "CLAUDE.md",
            "codex": self.home / ".codex" / "AGENTS.md",
            "gemini": self.home / ".gemini" / "GEMINI.md",
        }

    def skills(self):
        return [self.home / ".claude" / "skills" / "diavlo-mind", self.home / ".agents" / "skills" / "diavlo-mind",
                self.home / ".gemini" / "skills" / "diavlo-mind", self.home / ".gemini" / "config" / "skills" / "diavlo-mind"]

    def test_installs_everywhere_and_the_shared_gemini_file_gets_one_block(self):
        out = self.run_all("--hosts", ALL)
        for skill in self.skills():
            self.assertTrue((skill / "SKILL.md").is_file(), skill)
        for name, path in self.rules().items():
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count(install_all.MARK_BEGIN_PREFIX), 1, name)
            self.assertIn("diavlo-mind", text)
        self.assertIn("same file as Gemini CLI", out)
        self.assertTrue((self.home / ".codex" / "agents" / "dm-reviewer.toml").is_file())
        self.assertTrue((self.home / ".gemini" / "agents" / "dm-reviewer.md").is_file())

    def test_running_again_is_idempotent_and_leaves_no_backup_folders_among_the_skills(self):
        self.run_all("--hosts", ALL)
        before = {name: path.read_bytes() for name, path in self.rules().items()}
        out = self.run_all("--hosts", ALL)
        self.assertEqual(before, {name: path.read_bytes() for name, path in self.rules().items()})
        self.assertIn("already up to date", out)
        for skill in self.skills():
            self.assertEqual(list(skill.parent.glob("diavlo-mind.bak-*")), [], skill)
        for path in self.rules().values():
            self.assertEqual(list(path.parent.glob(path.name + ".bak-*")), [], path)

    def test_your_own_text_survives_install_and_uninstall_byte_for_byte(self):
        claude = self.rules()["claude"]
        claude.parent.mkdir(parents=True)
        original = "# Mis reglas\r\nResponde en español.\r\n".encode("utf-8")
        claude.write_bytes(original)
        self.run_all("--hosts", "claude-code")
        installed = claude.read_bytes()
        self.assertTrue(installed.startswith(original.rstrip(b"\r\n")))
        self.assertEqual(len(list(claude.parent.glob("CLAUDE.md.bak-*"))), 1)
        self.run_all("--uninstall", "--hosts", "claude-code")
        self.assertEqual(claude.read_bytes(), original)
        self.assertFalse(self.skills()[0].exists())

    def test_uninstall_removes_skills_agents_rules_and_the_files_it_created(self):
        self.run_all("--hosts", ALL)
        self.run_all("--uninstall", "--all")
        for skill in self.skills():
            self.assertFalse(skill.exists(), skill)
        for path in self.rules().values():
            self.assertFalse(path.exists(), path)
        self.assertFalse(list((self.home / ".codex" / "agents").glob("dm-*")))
        self.assertFalse(list((self.home / ".gemini" / "agents").glob("dm-*")))

    def test_dry_run_writes_nothing_at_all(self):
        out = self.run_all("--all", "--dry-run")
        self.assertIn("DRY RUN", out)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_only_the_tools_that_are_there_are_touched(self):
        (self.home / ".claude").mkdir()
        self.run_all()
        self.assertTrue(self.skills()[0].is_dir())
        self.assertTrue(self.rules()["claude"].is_file())
        self.assertFalse((self.home / ".codex").exists())
        self.assertFalse((self.home / ".gemini").exists())
        self.assertFalse((self.home / ".agents").exists())

    def test_nothing_found_means_nothing_written_and_a_clear_answer(self):
        out = self.run_all(expect=1)
        self.assertIn("No AI tool found", out)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_an_install_that_was_not_ours_is_moved_out_of_the_skills_folder(self):
        foreign = self.home / ".claude" / "skills" / "diavlo-mind"
        foreign.mkdir(parents=True)
        (foreign / "mine.txt").write_text("manual clone", encoding="utf-8")
        out = self.run_all("--hosts", "claude-code")
        self.assertIn("moved out of the skills folder", out)
        self.assertTrue((foreign / "SKILL.md").is_file())
        self.assertFalse((foreign / "mine.txt").exists())
        saved = list((self.home / ".diavlo-mind" / "backups").glob("claude-code-*/mine.txt"))
        self.assertEqual(len(saved), 1)
        self.assertEqual(list(foreign.parent.glob("diavlo-mind.bak-*")), [])

    def test_a_damaged_mark_stops_that_file_only_and_the_exit_code_says_so(self):
        gemini = self.rules()["gemini"]
        gemini.parent.mkdir(parents=True)
        gemini.write_text(install_all.MARK_BEGIN_PREFIX + " -->\nhalf a block\n", encoding="utf-8")
        before = gemini.read_bytes()
        out = self.run_all("--hosts", "claude-code,gemini-cli", expect=1)
        self.assertIn("damaged", out)
        self.assertEqual(gemini.read_bytes(), before)
        self.assertTrue(self.rules()["claude"].is_file(), "the other tool is still done")

    def test_skills_only_and_rules_only(self):
        self.run_all("--hosts", "claude-code", "--no-rules")
        self.assertTrue(self.skills()[0].is_dir())
        self.assertFalse(self.rules()["claude"].exists())
        self.run_all("--uninstall", "--hosts", "claude-code")
        self.run_all("--hosts", "claude-code", "--rules-only")
        self.assertFalse(self.skills()[0].exists())
        self.assertTrue(self.rules()["claude"].is_file())

    def test_spanish_rule_and_models_are_passed_to_the_agents(self):
        out = self.run_all("--hosts", "codex", "--lang", "es", "--executor-model", "gpt-test")
        self.assertIn("Hecho.", out)
        self.assertIn("método de trabajo por defecto", self.rules()["codex"].read_text(encoding="utf-8"))
        self.assertIn('model = "gpt-test"', (self.home / ".codex" / "agents" / "dm-executor.toml").read_text(encoding="utf-8"))

    def test_unknown_tool_is_an_error(self):
        out = subprocess.run([PY, str(SCRIPTS / "install_all.py"), "--hosts", "emacs"], capture_output=True, text=True,
                             env=dict(os.environ, DM_HOME=str(self.home)))
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("Unknown tool", out.stderr + out.stdout)


class BatchFileTests(unittest.TestCase):
    """install-all.bat cannot run on the CI machines that are not Windows, so its shape is checked."""

    def setUp(self):
        self.data = (ROOT / "install-all.bat").read_bytes()

    def test_crlf_only_and_plain_ascii(self):
        self.assertEqual(self.data.count(b"\n"), self.data.count(b"\r\n"), "a batch file needs CRLF line endings")
        self.assertFalse([byte for byte in self.data if byte > 127], "batch files are read in the console's code page: keep ASCII")

    def test_it_runs_the_script_with_the_arguments_it_was_given(self):
        text = self.data.decode("ascii")
        self.assertIn(r'"%~dp0scripts\install_all.py" %*', text)
        for interpreter in ('"py -3"', '"python"', '"python3"'):
            self.assertIn(interpreter, text)
        self.assertIn("sys.version_info >= (3, 9)", text)
        self.assertIn("exit /b %RC%", text)

    def test_git_keeps_it_as_written(self):
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("*.bat -text", attributes)

    @unittest.skipUnless(os.name == "nt", "needs Windows")
    def test_dry_run_through_the_real_batch_file(self):  # pragma: no cover - runs on the Windows CI job
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        env = dict(os.environ, DM_HOME=tmp.name)
        out = subprocess.run(["cmd", "/c", str(ROOT / "install-all.bat"), "--all", "--dry-run", "--lang", "en"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("DRY RUN", out.stdout)
        self.assertEqual(list(Path(tmp.name).iterdir()), [])


class SetupBatchFileTests(unittest.TestCase):
    """DIAVLO-MIND-Setup.bat: installs Python when missing, fetches the files when alone, then runs install_all.py."""

    def setUp(self):
        self.data = (ROOT / "DIAVLO-MIND-Setup.bat").read_bytes()
        self.text = self.data.decode("ascii")

    def test_crlf_only_and_plain_ascii(self):
        self.assertEqual(self.data.count(b"\n"), self.data.count(b"\r\n"), "a batch file needs CRLF line endings")
        self.assertFalse([byte for byte in self.data if byte > 127], "batch files are read in the console's code page: keep ASCII")

    def test_it_runs_the_installer_with_the_arguments_it_was_given(self):
        self.assertIn(r'%PYCMD% "%DM_SRC%scripts\install_all.py" %*', self.text)
        self.assertIn("sys.version_info >= (3, 9)", self.text)
        self.assertIn("exit /b %RC%", self.text)

    def test_python_is_installed_for_the_user_only_and_checked(self):
        self.assertIn("--scope user", self.text)
        self.assertIn("InstallAllUsers=0 InstallLauncherAllUsers=0", self.text)
        self.assertIn("Get-FileHash -Algorithm MD5", self.text)
        self.assertIn("Python Software Foundation", self.text)
        self.assertRegex(self.text, r'set "PY_MD5=[0-9a-f]{32}"')

    def test_it_downloads_from_this_repository_only_when_alone(self):
        self.assertIn(r'if exist "%~dp0SKILL.md" if exist "%~dp0scripts\install_all.py" goto havesource', self.text)
        self.assertIn("/releases/latest/download/DIAVLO-MIND-FABLE-EDITION.zip", self.text)
        metadata = json.loads((ROOT / ".github" / "repo-metadata.json").read_text(encoding="utf-8"))
        self.assertIn("DIAVLO-MIND-Setup.bat", metadata["release"]["assets"], "the setup file must be attached to releases")

    @unittest.skipUnless(os.name == "nt", "needs Windows")
    def test_dry_run_through_the_real_batch_file(self):  # pragma: no cover - runs on the Windows CI job
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        env = dict(os.environ, DM_HOME=tmp.name)
        out = subprocess.run(["cmd", "/c", str(ROOT / "DIAVLO-MIND-Setup.bat"), "--all", "--dry-run", "--lang", "en"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("OK: Python", out.stdout)
        self.assertIn("DRY RUN", out.stdout)
        self.assertEqual(list(Path(tmp.name).iterdir()), [])

    @unittest.skipUnless(os.name == "nt" and os.environ.get("CI"), "needs Windows and network (CI only)")
    def test_alone_in_an_empty_folder_it_downloads_the_files(self):  # pragma: no cover - runs on the Windows CI job
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "downloads").mkdir()
        alone = root / "downloads" / "DIAVLO-MIND-Setup.bat"
        alone.write_bytes(self.data)
        env = dict(os.environ, DM_HOME=str(root / "home"), USERPROFILE=str(root / "profile"))
        out = subprocess.run(["cmd", "/c", str(alone), "--all", "--dry-run", "--lang", "en"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        source = root / "profile" / ".diavlo-mind" / "source"
        self.assertTrue((source / "SKILL.md").is_file(), out.stdout + out.stderr)
        self.assertTrue((source / "scripts" / "install_all.py").is_file())
        self.assertIn("DRY RUN", out.stdout)
        self.assertFalse((root / "home").exists(), "a dry run writes nothing in the home folder")


if __name__ == "__main__":
    unittest.main()
