"""Tests for dm_llm.py (against a local mock HTTP server) and dm_orchestrate.py (scripted model)."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import dm_llm  # noqa: E402
import dm_orchestrate  # noqa: E402

PY = sys.executable


class FakeAPI(BaseHTTPRequestHandler):
    """Answers like the documented provider endpoints and records what it was sent."""
    requests = []
    fail_first = 0

    def log_message(self, *args):  # keep test output clean
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        FakeAPI.requests.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})
        if FakeAPI.fail_first > 0:
            FakeAPI.fail_first -= 1
            return self.reply(500, {"error": {"message": "temporary"}})
        if self.path == "/v1/messages":
            if "bad" in body.get("model", ""):
                return self.reply(400, {"type": "error", "error": {"type": "invalid_request_error", "message": "unknown model"}})
            return self.reply(200, {"type": "message", "role": "assistant", "stop_reason": "end_turn",
                                    "content": [{"type": "thinking", "thinking": "hidden"},
                                                {"type": "text", "text": "Hello "}, {"type": "text", "text": "Claude"}],
                                    "usage": {"input_tokens": 10, "cache_read_input_tokens": 5, "output_tokens": 3}})
        if self.path == "/v1/chat/completions":
            return self.reply(200, {"choices": [{"message": {"role": "assistant", "content": "Hello chat"}, "finish_reason": "stop"}],
                                    "usage": {"prompt_tokens": 7, "completion_tokens": 2, "total_tokens": 9}})
        if self.path == "/v1/responses":
            return self.reply(200, {"status": "completed", "output": [
                {"type": "reasoning", "summary": []},
                {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Hello responses", "annotations": []}]}],
                "usage": {"input_tokens": 8, "output_tokens": 4}})
        if self.path.startswith("/v1beta/models/") and self.path.endswith(":generateContent"):
            return self.reply(200, {"candidates": [{"content": {"role": "model", "parts": [
                {"text": "secret", "thought": True}, {"text": "Hello gemini"}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 6, "candidatesTokenCount": 2, "thoughtsTokenCount": 1, "totalTokenCount": 9}})
        return self.reply(404, {"error": "unknown path"})

    def reply(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class ProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeAPI)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        FakeAPI.requests.clear()
        FakeAPI.fail_first = 0
        env = {"ANTHROPIC_API_KEY": "k-ant", "OPENAI_API_KEY": "k-oai", "GEMINI_API_KEY": "k-gem",
               "DM_ANTHROPIC_BASE_URL": self.base, "DM_OPENAI_BASE_URL": self.base + "/v1", "DM_GEMINI_BASE_URL": self.base,
               "DM_HTTP_TIMEOUT": "10", "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in ("DM_ANTHROPIC_AUTH", "DM_ANTHROPIC_VERSION"):
            os.environ.pop(name, None)
        sleeper = mock.patch.object(dm_llm.time, "sleep", lambda seconds: None)
        sleeper.start()
        self.addCleanup(sleeper.stop)

    def ask(self, spec, **kwargs):
        return dm_llm.complete(spec, "Be brief.", [{"role": "user", "content": "Hi"}], **kwargs)

    def test_anthropic_request_and_response(self):
        result = self.ask("anthropic:claude-test")
        sent = FakeAPI.requests[-1]
        self.assertEqual(sent["path"], "/v1/messages")
        self.assertEqual(sent["headers"]["anthropic-version"], "2026-10-21")
        self.assertEqual(sent["headers"]["authorization"], "Bearer k-ant")
        self.assertNotIn("x-api-key", sent["headers"])
        self.assertEqual(sent["body"]["system"], "Be brief.")
        self.assertEqual(sent["body"]["messages"], [{"role": "user", "content": "Hi"}])
        self.assertGreater(sent["body"]["max_tokens"], 0)
        for removed in ("temperature", "top_p", "top_k"):
            self.assertNotIn(removed, sent["body"], "sampling parameters are rejected by API version 2026-10-21")
        self.assertEqual(result["text"], "Hello Claude", "thinking blocks must not leak into the text")
        self.assertEqual((result["input_tokens"], result["output_tokens"]), (15, 3))

    def test_anthropic_legacy_key_header(self):
        with mock.patch.dict(os.environ, {"DM_ANTHROPIC_AUTH": "x-api-key", "DM_ANTHROPIC_VERSION": "2023-06-01"}):
            self.ask("anthropic:claude-test")
        sent = FakeAPI.requests[-1]["headers"]
        self.assertEqual(sent["x-api-key"], "k-ant")
        self.assertEqual(sent["anthropic-version"], "2023-06-01")
        self.assertNotIn("authorization", sent)

    def test_openai_chat_uses_developer_role_and_no_token_cap_by_default(self):
        result = self.ask("openai:gpt-test")
        sent = FakeAPI.requests[-1]
        self.assertEqual(sent["path"], "/v1/chat/completions")
        self.assertEqual(sent["headers"]["authorization"], "Bearer k-oai")
        self.assertEqual(sent["body"]["messages"][0], {"role": "developer", "content": "Be brief."})
        self.assertNotIn("max_tokens", sent["body"])
        self.assertNotIn("max_completion_tokens", sent["body"])
        self.assertNotIn("temperature", sent["body"])
        self.assertEqual((result["text"], result["input_tokens"], result["output_tokens"]), ("Hello chat", 7, 2))
        self.ask("openai:gpt-test", max_tokens=100)
        self.assertEqual(FakeAPI.requests[-1]["body"]["max_completion_tokens"], 100)

    def test_compatible_server_uses_system_role_and_max_tokens(self):
        self.ask("compatible:llama", max_tokens=50)
        body = FakeAPI.requests[-1]["body"]
        self.assertEqual(body["messages"][0]["role"], "system")
        self.assertEqual(body["max_tokens"], 50)

    def test_openai_responses(self):
        result = self.ask("openai-responses:gpt-test")
        sent = FakeAPI.requests[-1]
        self.assertEqual(sent["path"], "/v1/responses")
        self.assertEqual(sent["body"]["instructions"], "Be brief.")
        self.assertEqual(sent["body"]["input"], [{"role": "user", "content": "Hi"}])
        self.assertEqual((result["text"], result["input_tokens"], result["output_tokens"]), ("Hello responses", 8, 4))

    def test_gemini(self):
        result = dm_llm.complete("gemini:gemini-test", "Be brief.", [
            {"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Yes?"}, {"role": "user", "content": "Go"}])
        sent = FakeAPI.requests[-1]
        self.assertEqual(sent["path"], "/v1beta/models/gemini-test:generateContent")
        self.assertEqual(sent["headers"]["x-goog-api-key"], "k-gem")
        self.assertEqual(sent["body"]["system_instruction"], {"parts": [{"text": "Be brief."}]})
        self.assertEqual([c["role"] for c in sent["body"]["contents"]], ["user", "model", "user"])
        self.assertEqual(result["text"], "Hello gemini", "thought parts must not leak into the text")
        self.assertEqual((result["input_tokens"], result["output_tokens"]), (6, 3))

    def test_retry_on_server_error_then_success(self):
        FakeAPI.fail_first = 2
        self.assertEqual(self.ask("openai:gpt-test")["text"], "Hello chat")
        self.assertEqual(len(FakeAPI.requests), 3)

    def test_client_error_is_reported_not_retried(self):
        with self.assertRaises(dm_llm.LLMError) as caught:
            self.ask("anthropic:bad-model")
        self.assertIn("HTTP 400", str(caught.exception))
        self.assertEqual(len(FakeAPI.requests), 1)

    def test_missing_key_and_bad_spec(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with self.assertRaises(dm_llm.LLMError):
                self.ask("openai:gpt-test")
        for spec in ("no-colon", "martian:model", "openai:"):
            with self.assertRaises(dm_llm.LLMError):
                self.ask(spec)

    def test_cmd_provider(self):
        command = f'"{PY}" -c "import sys; print(sys.stdin.read().upper())"'
        with mock.patch.dict(os.environ, {"DM_CMD": command}):
            result = self.ask("cmd:local")
        self.assertIn("BE BRIEF.", result["text"])
        self.assertIn("HI", result["text"])
        self.assertIsNone(result["input_tokens"])

    def test_mock_provider_checks_markers_and_runs_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script.json"
            script.write_text(json.dumps({"responses": ["one", {"contains": "Hi", "text": "two"}, {"contains": "absent", "text": "x"}]}))
            self.assertEqual(self.ask(f"mock:{script}")["text"], "one")
            self.assertEqual(self.ask(f"mock:{script}")["text"], "two")
            with self.assertRaises(dm_llm.LLMError):
                self.ask(f"mock:{script}")
            self.assertEqual(len(Path(str(script) + ".calls").read_text().splitlines()), 2)


PLAN = json.dumps({"objective": "calc.add works", "requirements": [{"id": "R1", "text": "add(a, b) returns a + b"}],
                   "tasks": [{"id": "T1", "title": "Write calc.py", "instructions": "Create calc.py with add()",
                              "files": ["calc.py"], "acceptance": ["check passes"], "requirements": ["R1"]}],
                   "assumptions": [], "questions": []})
WRONG = "=== FILE: calc.py ===\ndef add(a, b):\n    return a - b\n=== END FILE ===\n" + json.dumps({"status": "PARTIAL", "summary": "wrote it", "evidence": []})
RIGHT = "Root cause: subtraction instead of addition.\n=== FILE: calc.py ===\ndef add(a, b):\n    return a + b\n=== END FILE ===\n" + json.dumps({"status": "PARTIAL", "summary": "fixed", "evidence": []})
REVIEW_PASS = json.dumps({"verdict": "PASS", "coverage": [{"requirement": "R1", "covered": True, "where": "calc.py:2", "note": ""}], "findings": []})
CHECK = f'"{PY}" -c "import calc; assert calc.add(2, 3) == 5"'


class OrchestratorUnitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_file_blocks_are_written_and_fences_stripped(self):
        reply = "intro\n=== FILE: a/b.txt ===\nhello\nworld\n=== END FILE ===\n=== FILE: c.py ===\n```python\nx = 1\n```\n=== END FILE ===\n"
        changed, problems = dm_orchestrate.apply_reply(self.work, reply)
        self.assertEqual(changed, ["a/b.txt", "c.py"])
        self.assertEqual(problems, [])
        self.assertEqual((self.work / "a" / "b.txt").read_text(), "hello\nworld\n")
        self.assertEqual((self.work / "c.py").read_text(), "x = 1\n")

    def test_unsafe_paths_are_refused(self):
        outside = self.work.parent / "escaped.txt"
        for name in ("../escaped.txt", str(outside), ".git/config", ".diavlo-mind/state.json"):
            reply = f"=== FILE: {name} ===\nx\n=== END FILE ===\n"
            changed, problems = dm_orchestrate.apply_reply(self.work, reply)
            self.assertEqual(changed, [], name)
            self.assertEqual(len(problems), 1, name)
        self.assertFalse(outside.exists())

    def test_truncated_block_is_reported_and_not_written(self):
        changed, problems = dm_orchestrate.apply_reply(self.work, "=== FILE: a.txt ===\nhalf a file")
        self.assertEqual(changed, [])
        self.assertIn("not closed", problems[0])
        self.assertFalse((self.work / "a.txt").exists())

    def test_delete_and_dry_run(self):
        (self.work / "old.txt").write_text("x")
        changed, _ = dm_orchestrate.apply_reply(self.work, "=== DELETE: old.txt ===\n=== FILE: new.txt ===\ny\n=== END FILE ===", dry_run=True)
        self.assertTrue((self.work / "old.txt").exists())
        self.assertFalse((self.work / "new.txt").exists())
        self.assertEqual(len(changed), 2)
        dm_orchestrate.apply_reply(self.work, "=== DELETE: old.txt ===")
        self.assertFalse((self.work / "old.txt").exists())

    def test_extract_json_ignores_json_inside_files(self):
        reply = '=== FILE: data.json ===\n{"status": "inside a file"}\n=== END FILE ===\ntext {not json} {"status": "DONE", "n": 1}'
        self.assertEqual(dm_orchestrate.extract_json(reply, "status"), {"status": "DONE", "n": 1})
        self.assertIsNone(dm_orchestrate.extract_json("no json here", "status"))

    def test_snapshot_shows_text_and_lists_the_rest(self):
        (self.work / "a.py").write_text("print(1)\n")
        (self.work / "big.txt").write_text("x" * 5000)
        (self.work / "bin.dat").write_bytes(b"\xff\xfe\x00\x01")
        (self.work / ".git").mkdir()
        (self.work / ".git" / "config").write_text("secret")
        view = dm_orchestrate.snapshot(self.work, per_file=1000, total=10000)
        self.assertIn("--- a.py (2 lines) ---\nprint(1)", view)
        self.assertIn("big.txt (5000 bytes, not shown)", view)
        self.assertIn("bin.dat (binary or unreadable)", view)
        self.assertNotIn("secret", view)

    def test_core_rules_come_from_skill_file(self):
        rules = dm_orchestrate.core_rules()
        self.assertIn("Requirements are a list", rules)
        self.assertIn("Protect the user", rules)
        self.assertIn(rules, dm_orchestrate.executor_system())


class OrchestratorRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name) / "work"
        self.work.mkdir()
        self.addCleanup(self.tmp.cleanup)

    def script(self, name, responses):
        path = Path(self.tmp.name) / f"{name}.json"
        path.write_text(json.dumps({"responses": responses}), encoding="utf-8")
        return f"mock:{path}"

    def run_cli(self, *args):
        out = subprocess.run([PY, str(SCRIPTS / "dm_orchestrate.py"), "--task", "Create calc.py with add(a, b).",
                              "--workspace", str(self.work), "--json", "--quiet", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            return out.returncode, json.loads(out.stdout)
        except json.JSONDecodeError:
            self.fail(f"no JSON summary (exit {out.returncode}): {out.stdout}\n{out.stderr}")

    def test_standard_mode_plans_repairs_and_reviews(self):
        spec = self.script("std", [{"contains": "PLANNER", "text": PLAN}, {"contains": "TASK PACKET", "text": WRONG},
                                   {"contains": "CHECK OUTPUT", "text": RIGHT}, {"contains": "REVIEWER", "text": REVIEW_PASS}])
        code, summary = self.run_cli("--mode", "standard", "--executor", spec, "--check-cmd", CHECK)
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary["status"], "DONE")
        self.assertEqual(summary["repairs"], 1)
        self.assertEqual(summary["check"]["passed"], True)
        self.assertEqual(summary["review_verdict"], "PASS")
        self.assertEqual(set(summary["usage"]), {"planner", "executor", "reviewer"})
        self.assertIn("return a + b", (self.work / "calc.py").read_text())
        run_dir = Path(summary["run_dir"])
        report = (run_dir / "report.md").read_text(encoding="utf-8")
        self.assertIn("Status: DONE", report)
        self.assertIn("VERIFIED", report)
        self.assertIn("same model in a fresh context", report)
        self.assertEqual(len((run_dir / "transcript.jsonl").read_text(encoding="utf-8").splitlines()), 4)

    def test_raw_mode_reports_a_failing_check_as_failed(self):
        code, summary = self.run_cli("--mode", "raw", "--executor", self.script("raw", [WRONG]), "--check-cmd", CHECK)
        self.assertEqual(code, 1)
        self.assertEqual(summary["status"], "FAILED")
        self.assertEqual(summary["repairs"], 0)

    def test_without_a_check_the_result_is_only_partial(self):
        code, summary = self.run_cli("--mode", "fast", "--executor", self.script("nocheck", [RIGHT]))
        self.assertEqual(code, 1)
        self.assertEqual(summary["status"], "PARTIAL", "nothing was executed, so it cannot be DONE")
        self.assertIn("NOT RUN", (Path(summary["run_dir"]) / "report.md").read_text(encoding="utf-8"))

    def test_advisor_takes_over_after_executor_repairs_fail(self):
        executor = self.script("weak", [WRONG, WRONG, WRONG])
        advisor = self.script("strong", [{"contains": "PLANNER", "text": PLAN}, {"contains": "taking over", "text": RIGHT},
                                         {"contains": "REVIEWER", "text": REVIEW_PASS}])
        code, summary = self.run_cli("--mode", "standard", "--executor", executor, "--advisor", advisor, "--check-cmd", CHECK)
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary["escalations"], 1)
        self.assertEqual(summary["repairs"], 2)
        self.assertIn("advisor-escalation", summary["usage"])

    def test_reviewer_blocker_triggers_one_more_repair(self):
        blocker = json.dumps({"verdict": "FAIL", "coverage": [], "findings": [
            {"severity": "blocker", "where": "calc.py:1", "finding": "no docstring required by R1", "suggestion": "add it"}]})
        better = "Root cause: missing.\n=== FILE: calc.py ===\ndef add(a, b):\n    \"\"\"Add.\"\"\"\n    return a + b\n=== END FILE ===\n{\"status\": \"PARTIAL\"}"
        spec = self.script("blk", [PLAN, RIGHT, blocker, {"contains": "REVIEWER BLOCKERS", "text": better}])
        code, summary = self.run_cli("--mode", "standard", "--executor", spec, "--check-cmd", CHECK)
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary["repairs"], 1)
        self.assertIn('"""Add."""', (self.work / "calc.py").read_text())

    def test_deep_mode_runs_each_task_and_dry_run_writes_nothing(self):
        plan = json.loads(PLAN)
        plan["tasks"].append({"id": "T2", "title": "Write notes", "instructions": "Create NOTES.md", "files": ["NOTES.md"],
                              "acceptance": [], "requirements": ["R1"]})
        notes = "=== FILE: NOTES.md ===\nadd() adds.\n=== END FILE ===\n{\"status\": \"PARTIAL\"}"
        spec = self.script("deep", [json.dumps(plan), RIGHT, notes, REVIEW_PASS])
        code, summary = self.run_cli("--mode", "deep", "--executor", spec, "--check-cmd", CHECK)
        self.assertEqual(code, 0, summary)
        self.assertEqual(sorted(summary["files_written"]), ["NOTES.md", "calc.py"])
        self.assertEqual(summary["usage"]["executor"]["calls"], 2)

        other = Path(self.tmp.name) / "dry"
        other.mkdir()
        out = subprocess.run([PY, str(SCRIPTS / "dm_orchestrate.py"), "--task", "x", "--workspace", str(other), "--mode", "raw",
                              "--executor", self.script("dry", [RIGHT]), "--dry-run", "--quiet", "--run-dir", str(Path(self.tmp.name) / "dryrun")],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(list(other.iterdir()), [], out.stderr)

    def test_call_budget_stops_runaway_runs(self):
        spec = self.script("budget", [PLAN, WRONG, WRONG, WRONG])
        out = subprocess.run([PY, str(SCRIPTS / "dm_orchestrate.py"), "--task", "x", "--workspace", str(self.work), "--mode", "standard",
                              "--executor", spec, "--check-cmd", CHECK, "--max-calls", "3", "--quiet"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(out.returncode, 2)
        self.assertIn("call budget", out.stderr)


if __name__ == "__main__":
    unittest.main()
