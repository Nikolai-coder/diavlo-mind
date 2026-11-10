"""Tests for select_mode.py, dm_schema.py, dm_state.py and dm_packet.py."""
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

import dm_packet  # noqa: E402
import dm_schema  # noqa: E402
import dm_state  # noqa: E402
import select_mode  # noqa: E402


def run(script: str, *args: str, cwd=None, env=None):
    full_env = dict(os.environ, DM_NOW="2026-01-02T03:04:05Z")
    full_env.update(env or {})
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                          cwd=cwd, env=full_env)


class SelectModeTests(unittest.TestCase):
    def test_fast_for_single_clear_step(self):
        self.assertEqual(select_mode.recommend(steps=1, files=1)["mode"], "FAST")

    def test_standard_for_a_few_files(self):
        result = select_mode.recommend(steps=6, files=4, unknowns=1)
        self.assertEqual(result["mode"], "STANDARD")
        self.assertEqual(result["suggested_agents"], [])

    def test_standard_with_moderate_risk_suggests_reviewer(self):
        self.assertEqual(select_mode.recommend(steps=4, files=2, risk="moderate")["suggested_agents"], ["reviewer"])

    def test_deep_triggers(self):
        for kwargs in ({"unknowns": 2}, {"risk": "high"}, {"prior_failures": 1}, {"ambiguity": "high"},
                       {"components": 2, "files": 6}):
            self.assertEqual(select_mode.recommend(steps=3, **kwargs)["mode"], "DEEP", kwargs)

    def test_autonomous_triggers(self):
        for kwargs in ({"sessions": 2}, {"steps": 16}, {"files": 16}, {"components": 4}):
            self.assertEqual(select_mode.recommend(**kwargs)["mode"], "AUTONOMOUS", kwargs)

    def test_irreversible_always_needs_approval_note(self):
        notes = select_mode.recommend(steps=1, risk="irreversible")["notes"]
        self.assertTrue(any("approval" in note for note in notes))

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            select_mode.recommend(steps=-1)
        with self.assertRaises(ValueError):
            select_mode.recommend(risk="extreme")

    def test_mode_files_exist(self):
        for path in select_mode.MODE_FILE.values():
            self.assertTrue((ROOT / path).is_file(), path)

    def test_cli_json(self):
        out = run("select_mode.py", "--steps", "20", "--sessions", "2", "--json")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)["mode"], "AUTONOMOUS")


class SchemaTests(unittest.TestCase):
    def test_validator_reports_each_kind_of_error(self):
        schema = {"type": "object", "required": ["a"], "additionalProperties": False, "properties": {
            "a": {"type": "string", "minLength": 2, "pattern": "^x"},
            "b": {"type": "array", "minItems": 1, "items": {"enum": ["p", "q"]}},
            "c": {"type": "integer", "minimum": 0},
            "d": {"const": 1}}}
        self.assertEqual(dm_schema.validate({"a": "xy", "b": ["p"], "c": 0, "d": 1}, schema), [])
        errors = dm_schema.validate({"a": "y", "b": [], "c": -1, "d": 2, "z": 1}, schema)
        text = "\n".join(errors)
        for fragment in ("shorter than 2", "does not match", "at least 1", "below the minimum", "must be 1", "unknown field 'z'"):
            self.assertIn(fragment, text)
        self.assertIn("missing required field 'a'", dm_schema.validate({}, schema)[0])
        self.assertIn("expected object", dm_schema.validate([], schema)[0])
        self.assertIn("not one of", dm_schema.validate({"a": "xy", "b": ["r"]}, schema)[0])
        self.assertTrue(dm_schema.validate({"a": "xy", "c": True}, schema), "booleans are not integers")

    def test_agrees_with_reference_implementation_when_available(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        task = dm_packet.new_task("T1", "executor", "Build the export filter", "STANDARD")
        task["constraints"]["may_write"] = ["src/a.py"]
        result = dm_packet.new_result("T1", "executor")
        broken_task = dict(task, role="wizard")
        broken_result = dict(result, status="MAYBE")
        cases = [("task-packet.schema.json", task, True), ("task-packet.schema.json", broken_task, False),
                 ("result-packet.schema.json", result, True), ("result-packet.schema.json", broken_result, False)]
        for name, instance, expected in cases:
            schema = dm_schema.load_schema(name)
            reference_ok = not list(jsonschema.Draft202012Validator(schema).iter_errors(instance))
            ours_ok = not dm_schema.validate(instance, schema)
            self.assertEqual(reference_ok, expected, name)
            self.assertEqual(ours_ok, reference_ok, name)


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def state(self, *args):
        return run("dm_state.py", *args, "--dir", self.dir)

    def ok(self, *args):
        out = self.state(*args)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        return out.stdout.strip()

    def load(self):
        return json.loads((Path(self.dir) / ".diavlo-mind" / "state.json").read_text(encoding="utf-8"))

    def build(self):
        self.ok("init", "--objective", "Ship the filter", "--mode", "autonomous", "--done", "tests pass")
        self.assertEqual(self.ok("req", "add", "Export accepts --since"), "R1")
        self.assertEqual(self.ok("req", "add", "README documents it", "--type", "format"), "R2")
        self.assertEqual(self.ok("task", "add", "Parse flag", "--req", "R1", "--accept", "pytest -q", "--files", "src/export.py"), "T1")
        self.assertEqual(self.ok("task", "add", "Docs", "--req", "R2", "--depends", "T1", "--files", "README.md"), "T2")

    def test_init_refuses_to_overwrite(self):
        self.ok("init", "--objective", "A")
        self.assertEqual(self.state("init", "--objective", "B").returncode, 2)
        self.ok("init", "--objective", "B", "--force")
        self.assertEqual(self.load()["objective"], "B")

    def test_state_matches_schema(self):
        self.build()
        self.assertEqual(dm_schema.validate(self.load(), dm_schema.load_schema("state.schema.json")), [])
        self.assertEqual(self.load()["updated"], "2026-01-02T03:04:05Z")

    def test_ready_queue_respects_dependencies(self):
        self.build()
        self.assertIn("T1", self.ok("next"))
        self.assertNotIn("T2", self.ok("next"))
        self.assertEqual(self.state("task", "set", "T2", "--status", "doing").returncode, 2)
        self.ok("task", "set", "T1", "--status", "done", "--evidence", "pytest -> 6 passed")
        self.assertIn("T2", self.ok("next"))

    def test_done_needs_evidence_and_dropped_needs_reason(self):
        self.build()
        self.assertEqual(self.state("task", "set", "T1", "--status", "done").returncode, 2)
        self.assertEqual(self.state("task", "set", "T1", "--status", "dropped").returncode, 2)
        self.assertEqual(self.state("req", "set", "R1", "--status", "met").returncode, 2)
        self.ok("task", "set", "T1", "--status", "dropped", "--note", "not needed")

    def test_repeated_failures_trigger_a_warning(self):
        self.build()
        for _ in range(2):
            self.ok("task", "set", "T1", "--status", "doing")
            out = self.state("task", "set", "T1", "--status", "todo", "--note", "check failed")
        self.assertIn("failed 2 times", out.stderr)
        self.assertEqual(self.load()["tasks"][0]["attempts"], 2)
        self.assertIn("failed 2 times", self.ok("resume"))

    def test_parallel_conflict_is_flagged(self):
        self.build()
        self.ok("task", "add", "Tests", "--req", "R1", "--files", "src/export.py")
        self.assertIn("conflicts with T1", self.ok("next"))

    def test_validate_finds_cycles_and_dangling_references(self):
        self.build()
        self.assertIn("consistent", self.ok("validate"))
        path = Path(self.dir) / ".diavlo-mind" / "state.json"
        state = self.load()
        state["tasks"][0]["depends_on"] = ["T2"]
        state["tasks"][1]["requirements"] = ["R9"]
        path.write_text(json.dumps(state), encoding="utf-8")
        out = self.state("validate")
        self.assertEqual(out.returncode, 1)
        self.assertIn("dependency cycle", out.stdout)
        self.assertIn("unknown requirement R9", out.stdout)

    def test_uncovered_requirement_is_reported(self):
        self.build()
        self.ok("req", "add", "Nobody planned this")
        out = self.state("validate")
        self.assertEqual(out.returncode, 1)
        self.assertIn("R3 is not covered by any task", out.stdout)

    def test_done_check_only_passes_with_proof(self):
        self.build()
        out = self.state("done-check")
        self.assertEqual(out.returncode, 1)
        self.assertIn("NOT DONE", out.stdout)
        self.ok("task", "set", "T1", "--status", "done", "--evidence", "pytest -> 6 passed")
        self.ok("task", "set", "T2", "--status", "done", "--evidence", "README diff")
        self.ok("req", "set", "R1", "--status", "met", "--evidence", "6 tests")
        self.assertEqual(self.state("done-check").returncode, 1)
        self.ok("req", "set", "R2", "--status", "waived", "--evidence", "user waived on 2026-01-02")
        self.assertIn("DONE", self.ok("done-check"))

    def test_checkpoint_report_and_resume(self):
        self.build()
        self.ok("decision", "Use SQLite", "--why", "survives restart", "--revisit-if", "more than one host")
        self.ok("checkpoint", "T1 half done", "--next", "finish the parser", "--question", "inclusive date?")
        report = (Path(self.dir) / ".diavlo-mind" / "STATE.md").read_text(encoding="utf-8")
        for fragment in ("Ship the filter", "| R1 |", "| T2 |", "Use SQLite", "finish the parser"):
            self.assertIn(fragment, report)
        resume = self.ok("resume")
        for fragment in ("RESUME BRIEF", "finish the parser", "inclusive date?", "T1 Parse flag", "verify the claims"):
            self.assertIn(fragment, resume)

    def test_missing_state_is_a_clear_error(self):
        out = self.state("next")
        self.assertEqual(out.returncode, 2)
        self.assertIn("init", out.stderr)

    def test_cycle_detection_unit(self):
        tasks = [{"id": "T1", "depends_on": ["T3"]}, {"id": "T2", "depends_on": ["T1"]}, {"id": "T3", "depends_on": ["T2"]}]
        cycle = dm_state.find_cycle(tasks)
        self.assertIsNotNone(cycle)
        self.assertEqual(cycle[0], cycle[-1])
        self.assertIsNone(dm_state.find_cycle([{"id": "T1", "depends_on": []}, {"id": "T2", "depends_on": ["T1"]}]))


class PacketTests(unittest.TestCase):
    def good_task(self):
        packet = dm_packet.new_task("T7", "executor", "The export command accepts --since", "STANDARD")
        packet["constraints"]["may_write"] = ["src/export.py"]
        return packet

    def good_result(self):
        return {"type": "result", "id": "T7", "role": "executor", "status": "DONE", "summary": "Added the flag.",
                "evidence": [{"requirement": "R1", "status": "met", "level": "VERIFIED", "proof": "pytest -> 6 passed"}]}

    def test_valid_packets_pass(self):
        self.assertEqual(dm_packet.check(self.good_task()), [])
        self.assertEqual(dm_packet.check(self.good_result()), [])

    def test_executor_needs_writable_paths(self):
        packet = self.good_task()
        packet["constraints"]["may_write"] = []
        self.assertIn("writable paths", " ".join(dm_packet.check(packet)))

    def test_reviewer_must_not_write(self):
        packet = self.good_task()
        packet["role"] = "reviewer"
        self.assertIn("does not modify", " ".join(dm_packet.check(packet)))

    def test_done_requires_proof(self):
        for mutate, fragment in (
            (lambda p: p["evidence"][0].update(status="unmet"), "unmet or not verified"),
            (lambda p: p["evidence"][0].pop("proof"), "needs a proof"),
            (lambda p: p["evidence"][0].update(level="ASSUMED"), "ASSUMED or UNKNOWN"),
            (lambda p: p.update(evidence=[]), "at least one evidence"),
            (lambda p: p.update(issues=[{"severity": "blocker", "finding": "broken"}]), "open blocker"),
        ):
            packet = self.good_result()
            mutate(packet)
            self.assertIn(fragment, " ".join(dm_packet.check(packet)), fragment)

    def test_blocked_must_say_what_is_needed(self):
        packet = self.good_result()
        packet.update(status="BLOCKED", evidence=[])
        self.assertIn("BLOCKED must say", " ".join(dm_packet.check(packet)))

    def test_unknown_type_and_fields(self):
        self.assertTrue(dm_packet.check({"type": "memo"}))
        packet = self.good_task()
        packet["surprise"] = 1
        self.assertIn("unknown field 'surprise'", " ".join(dm_packet.check(packet)))

    def test_render_contains_every_section(self):
        text = dm_packet.render(self.good_task())
        for fragment in ("TASK PACKET", "id: T7", "may write: src/export.py", "acceptance:", "RESULT PACKET"):
            self.assertIn(fragment, text)
        text = dm_packet.render(self.good_result())
        self.assertIn("R1: met — VERIFIED — pytest -> 6 passed", text)

    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"
            self.assertEqual(run("dm_packet.py", "new", "task", "--id", "T1", "--role", "executor", "-o", str(path)).returncode, 0)
            out = run("dm_packet.py", "validate", str(path))
            self.assertEqual(out.returncode, 1, "an unfilled executor template must not validate")
            path.write_text(json.dumps(self.good_task()), encoding="utf-8")
            self.assertEqual(run("dm_packet.py", "validate", str(path)).returncode, 0)
            self.assertIn("TASK PACKET", run("dm_packet.py", "render", str(path)).stdout)


if __name__ == "__main__":
    unittest.main()
