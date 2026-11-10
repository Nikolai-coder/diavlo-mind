"""Tests for install.py, build_prompts.py, package.py, dm_improve.py and the repository validator."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_prompts  # noqa: E402
import dm_orchestrate  # noqa: E402
import install  # noqa: E402
import validate  # noqa: E402

PY = sys.executable
AGENTS = ["dm-architect", "dm-executor", "dm-optimizer", "dm-orchestrator", "dm-planner", "dm-researcher",
          "dm-reviewer", "dm-validator"]


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.addCleanup(self.tmp.cleanup)

    def run_install(self, *args, expect=0):
        env = dict(os.environ, DM_HOME=str(self.home))
        env.pop("CODEX_HOME", None)
        out = subprocess.run([PY, str(SCRIPTS / "install.py"), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        self.assertEqual(out.returncode, expect, out.stdout + out.stderr)
        return out.stdout

    def test_claude_code_install_is_a_valid_lean_skill_and_plugin(self):
        self.run_install("claude-code")
        skill = self.home / ".claude" / "skills" / "diavlo-mind"
        for name in ("SKILL.md", "LICENSE", "VERSION", ".claude-plugin/plugin.json", "scripts/dm_state.py",
                     "workflows/modes/fast.md", "agents/dm-reviewer.md", "memory/schemas/state.schema.json"):
            self.assertTrue((skill / name).is_file(), name)
        for name in ("evaluation", "tests", ".git", ".claude-plugin/marketplace.json", "scripts/validate.py"):
            self.assertFalse((skill / name).exists(), f"{name} should not be in a lean install")
        self.assertFalse(list(skill.rglob("__pycache__")))
        manifest = json.loads((skill / ".dm-install.json").read_text())
        self.assertEqual(manifest["target"], "claude-code")
        # the installed scripts must work from their new location
        project = Path(self.tmp.name) / "project"
        project.mkdir()
        out = subprocess.run([PY, str(skill / "scripts" / "dm_state.py"), "init", "--objective", "x", "--dir", str(project)],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(subprocess.run([PY, str(skill / "scripts" / "dm_state.py"), "validate", "--dir", str(project)],
                                        capture_output=True, text=True, encoding="utf-8", errors="replace").returncode, 0)

    def test_existing_install_is_backed_up_unless_forced(self):
        self.run_install("claude-code")
        self.run_install("claude-code")
        skills = self.home / ".claude" / "skills"
        self.assertEqual(len([p for p in skills.iterdir() if ".bak-" in p.name]), 1)
        self.run_install("claude-code", "--force")
        self.assertEqual(len([p for p in skills.iterdir() if ".bak-" in p.name]), 1)

    def test_dry_run_writes_nothing(self):
        out = self.run_install("claude-code", "--dry-run")
        self.assertIn("would copy skill", out)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_hybrid_models_are_applied_by_role_class(self):
        self.run_install("claude-code", "--executor-model", "haiku", "--advisor-model", "opus")
        agents = self.home / ".claude" / "skills" / "diavlo-mind" / "agents"
        for name in AGENTS:
            text = (agents / f"{name}.md").read_text(encoding="utf-8")
            expected = "haiku" if name in install.EXECUTOR_CLASS else "opus"
            self.assertIn(f"\nmodel: {expected}\n", text, name)
        self.assertEqual(install.EXECUTOR_CLASS | install.ADVISOR_CLASS, set(AGENTS))

    def test_project_scope_and_other_targets(self):
        project = Path(self.tmp.name) / "proj"
        project.mkdir()
        self.run_install("claude-code", "--scope", "project", "--project", str(project))
        self.assertTrue((project / ".claude" / "skills" / "diavlo-mind" / "SKILL.md").is_file())
        self.run_install("agents")
        self.assertTrue((self.home / ".agents" / "skills" / "diavlo-mind" / "SKILL.md").is_file())
        self.assertFalse((self.home / ".agents" / "skills" / "diavlo-mind" / ".claude-plugin").exists())
        self.run_install("antigravity")
        self.assertTrue((self.home / ".gemini" / "config" / "skills" / "diavlo-mind" / "SKILL.md").is_file())
        self.run_install("antigravity", "--scope", "project", "--project", str(project))
        self.assertTrue((project / ".agents" / "skills" / "diavlo-mind" / "SKILL.md").is_file())
        custom = Path(self.tmp.name) / "anywhere"
        self.run_install("custom", "--dest", str(custom))
        self.assertTrue((custom / "diavlo-mind" / "SKILL.md").is_file())
        self.run_install("custom", expect=1)

    def test_codex_agents_are_valid_toml(self):
        self.run_install("codex", "--with-agents", "--executor-model", "small-model")
        folder = self.home / ".codex" / "agents"
        self.assertEqual(sorted(p.stem for p in folder.glob("*.toml")), AGENTS)
        try:
            import tomllib
        except ImportError:
            self.skipTest("tomllib needs Python 3.11+")
        for name in AGENTS:
            data = tomllib.loads((folder / f"{name}.toml").read_text(encoding="utf-8"))
            self.assertEqual(data["name"], name)
            self.assertGreater(len(data["description"]), 40)
            _, body = install.split_frontmatter((ROOT / "agents" / f"{name}.md").read_text(encoding="utf-8"))
            self.assertEqual(data["developer_instructions"].strip(), body.strip(), name)
            self.assertEqual(data.get("model"), "small-model" if name in install.EXECUTOR_CLASS else None)

    def test_toml_escaping_survives_awkward_bodies(self):
        try:
            import tomllib
        except ImportError:
            self.skipTest("tomllib needs Python 3.11+")
        body = "Use '''triple''' quotes, a \\ backslash and \"\"\"doubles\"\"\".\n"
        text = install.to_codex_toml({"name": "x", "description": 'say "hi"'}, body, None)
        data = tomllib.loads(text)
        self.assertEqual(data["developer_instructions"].strip(), body.strip())
        self.assertEqual(data["description"], 'say "hi"')

    def test_gemini_agents_drop_claude_specific_fields(self):
        self.run_install("gemini-cli", "--with-agents")
        folder = self.home / ".gemini" / "agents"
        self.assertEqual(sorted(p.stem for p in folder.glob("*.md")), AGENTS)
        meta, body = install.split_frontmatter((folder / "dm-reviewer.md").read_text(encoding="utf-8"))
        self.assertEqual(set(meta), {"name", "description"})
        self.assertIn("You are the REVIEWER", body)

    def test_uninstall_removes_skill_and_generated_agents(self):
        self.run_install("codex", "--with-agents")
        self.run_install("codex", "--uninstall")
        self.assertFalse((self.home / ".agents" / "skills" / "diavlo-mind").exists())
        self.assertEqual(list((self.home / ".codex" / "agents").glob("*.toml")), [])
        self.assertIn("nothing installed", self.run_install("codex", "--uninstall"))


class BuildAndValidateTests(unittest.TestCase):
    def test_prompts_are_in_sync_and_within_limits(self):
        out = subprocess.run([PY, str(SCRIPTS / "build_prompts.py"), "--check"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_core_rules_are_identical_everywhere(self):
        rules = build_prompts.core_rules()
        self.assertEqual(len([line for line in rules.splitlines() if line[:1].isdigit()]), 10)
        for name in ("diavlo-mind-compact.md", "diavlo-mind-standard.md", "diavlo-mind-full.md"):
            self.assertIn(rules.strip(), (ROOT / "prompts" / "system" / name).read_text(encoding="utf-8"), name)

    def test_size_limits_are_enforced(self):
        path = ROOT / "prompts" / "system" / "diavlo-mind-micro.md"
        self.assertEqual(build_prompts.size_problems({path: "x" * 1500}), [])
        self.assertEqual(len(build_prompts.size_problems({path: "x" * 1501})), 1)

    def test_full_bundle_contains_every_skill_file(self):
        bundle = (ROOT / "prompts" / "system" / "diavlo-mind-full.md").read_text(encoding="utf-8")
        for folder, pattern in (("workflows/modes", "*.md"), ("workflows/procedures", "*.md"),
                                ("workflows/protocols", "*.md"), ("agents", "dm-*.md")):
            for path in (ROOT / folder).glob(pattern):
                self.assertIn(f"FILE: {path.relative_to(ROOT).as_posix()}", bundle)

    def test_repository_validates(self):
        report = validate.run(release=False)
        problems = [f"{name}: {error}" for name, errors, _, _ in report.sections for error in errors]
        self.assertEqual(problems, [])

    def test_validator_catches_a_changed_core_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "diavlo-mind"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "dist", "runs", "__pycache__", "results"))
            skill = copy / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8").replace("Never run the same failing action a third time.",
                                                                        "Retry as often as you like."), encoding="utf-8")
            out = subprocess.run([PY, str(copy / "scripts" / "validate.py"), "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(out.returncode, 1)
            failed = {check["name"]: check["errors"] for check in json.loads(out.stdout)["checks"] if not check["ok"]}
            self.assertIn("Core rules lock", failed)
            self.assertIn("approve-core-change", failed["Core rules lock"][0])
            self.assertIn("Prompt tiers in sync", failed, "prompt copies of the rules must also be flagged as stale")
            # the documented path makes it pass again, and leaves a record
            subprocess.run([PY, str(copy / "scripts" / "build_prompts.py")], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
            subprocess.run([PY, str(copy / "scripts" / "dm_improve.py"), "approve-core-change", "--reason",
                            "Test: demonstrating the approval path for a rule change."], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
            out = subprocess.run([PY, str(copy / "scripts" / "validate.py"), "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            still_failed = [check["name"] for check in json.loads(out.stdout)["checks"] if not check["ok"]]
            self.assertNotIn("Core rules lock", still_failed)
            self.assertIn("demonstrating the approval path", (copy / "evaluation" / "improvement" / "improvement-log.md").read_text(encoding="utf-8"))

    def test_validator_catches_structural_damage(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "diavlo-mind"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "dist", "runs", "__pycache__", "results"))
            (copy / "workflows" / "procedures" / "p07-debugging-recovery.md").unlink()
            (copy / "agents" / "notes.md").write_text("stray file", encoding="utf-8")
            text = (copy / "agents" / "dm-planner.md").read_text(encoding="utf-8")
            (copy / "agents" / "dm-planner.md").write_text(text.replace("## Boundaries", "## Limits"), encoding="utf-8")
            out = subprocess.run([PY, str(copy / "scripts" / "validate.py"), "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            errors = " ".join(e for check in json.loads(out.stdout)["checks"] for e in check["errors"])
            for fragment in ("p07-", "agents/notes.md", "missing section '## Boundaries'", "referenced path does not exist"):
                self.assertIn(fragment, errors)

    def test_frontmatter_parser_without_yaml(self):
        text = '---\nname: x\ndescription: "a: b"\nmetadata:\n  version: "1.0.0"\n---\nbody\n'
        saved, validate.yaml = validate.yaml, None
        try:
            meta, body, problem = validate.parse_frontmatter(text)
        finally:
            validate.yaml = saved
        self.assertEqual(problem, "")
        self.assertEqual(meta, {"name": "x", "description": "a: b", "metadata": {"version": "1.0.0"}})
        self.assertEqual(body, "body\n")


class PackageAndImproveTests(unittest.TestCase):
    def test_archives_have_the_documented_layout(self):
        out = subprocess.run([PY, str(SCRIPTS / "package.py")], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        with zipfile.ZipFile(ROOT / "dist" / "DIAVLO-MIND-FABLE-EDITION.zip") as archive:
            names = archive.namelist()
        for name in ("SKILL.md", "README.md", "INSTALL.md", "ARCHITECTURE.md", "CHANGELOG.md"):
            self.assertIn(f"DIAVLO-MIND/{name}", names)
        for folder in ("prompts", "agents", "workflows", "adapters", "memory", "evaluation", "scripts", "examples"):
            self.assertTrue(any(n.startswith(f"DIAVLO-MIND/{folder}/") for n in names), folder)
        self.assertFalse(any("__pycache__" in n or "/.git/" in n or "/runs/" in n for n in names))
        with zipfile.ZipFile(ROOT / "dist" / "diavlo-mind.zip") as archive:
            lean = archive.namelist()
        self.assertIn("diavlo-mind/SKILL.md", lean)
        self.assertFalse(any(n.startswith("diavlo-mind/evaluation/") for n in lean))
        self.assertLess((ROOT / "dist" / "diavlo-mind.zip").stat().st_size, 30 * 1024 * 1024, "Skills API upload limit")

    def test_improvement_log_requires_evidence_to_accept(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "diavlo-mind"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "dist", "runs", "__pycache__", "results"))
            # The repository ships real failure records; the test starts from an empty record file.
            (copy / "evaluation" / "improvement" / "failures.jsonl").unlink(missing_ok=True)
            tool = [PY, str(copy / "scripts" / "dm_improve.py")]
            record = subprocess.run(tool + ["record", "--task", "debugging", "--model", "m", "--arm", "diavlo-mind",
                                            "--observed", "retried the same command 4 times", "--expected", "change approach after 2"],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(record.stdout.strip(), "F1")
            undecided = subprocess.run(tool + ["decide", "--id", "F1", "--decision", "rejected", "--note", "n"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertNotEqual(undecided.returncode, 0, "must classify before deciding")
            subprocess.run(tool + ["classify", "--id", "F1", "--category", "inadequate_instructions", "--hypothesis", "h", "--change", "p07"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
            blind = subprocess.run(tool + ["decide", "--id", "F1", "--decision", "accepted", "--note", "looks better"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertNotEqual(blind.returncode, 0, "accepting without benchmark runs must be refused")
            base, cand = Path(tmp) / "base", Path(tmp) / "cand"
            for folder, rate in ((base, 0.75), (cand, 0.5)):
                folder.mkdir()
                (folder / "summary.json").write_text(json.dumps({"overall": {"success_rate": rate}}))
            worse = subprocess.run(tool + ["decide", "--id", "F1", "--decision", "accepted", "--note", "n", "--baseline", str(base),
                                           "--candidate", str(cand)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertNotEqual(worse.returncode, 0, "a change that lowers overall success must be refused")
            ok = subprocess.run(tool + ["decide", "--id", "F1", "--decision", "rejected", "--note", "0.75 -> 0.50 overall", "--baseline",
                                        str(base), "--candidate", str(cand)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIn("F1 — rejected", (copy / "evaluation" / "improvement" / "improvement-log.md").read_text(encoding="utf-8"))


class BytecodeRegressionTest(unittest.TestCase):
    def test_rewritten_python_file_loses_its_cached_bytecode(self):
        """Regression: a one-character repair in the same second was tested against stale bytecode."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "__pycache__").mkdir()
            cached = work / "__pycache__" / "calc.cpython-313.pyc"
            other = work / "__pycache__" / "calculus.cpython-313.pyc"
            cached.write_bytes(b"stale")
            other.write_bytes(b"unrelated")
            dm_orchestrate.apply_reply(work, "=== FILE: calc.py ===\ndef add(a, b):\n    return a + b\n=== END FILE ===\n")
            self.assertFalse(cached.exists())
            self.assertTrue(other.exists(), "bytecode of other modules must be left alone")


if __name__ == "__main__":
    unittest.main()
