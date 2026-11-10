"""End-to-end test of the benchmark tooling without any model: run, re-score, score, compare, export."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "evaluation"
TASKS = ["programming-duration", "research-kestrel"]


def run(script, *args):
    return subprocess.run([sys.executable, str(EVAL / script), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=str(ROOT))


class BenchmarkPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        cls.outputs = {}
        for runner in ("null", "reference"):
            done = run("run_benchmark.py", "--runner", runner, "--tasks", *TASKS, "--keep-workspaces",
                       "--out", cls.base / runner)
            cls.outputs[runner] = done

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def results(self, runner):
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((self.base / runner).rglob("result.json"))]

    def test_harness_scores_empty_work_as_failed_and_reference_as_solved(self):
        for runner in ("null", "reference"):
            self.assertEqual(self.outputs[runner].returncode, 0, self.outputs[runner].stderr)
            self.assertEqual(len(self.results(runner)), len(TASKS))
        self.assertFalse(any(r["success"] for r in self.results("null")))
        self.assertTrue(all(r["success"] for r in self.results("reference")))
        self.assertTrue(all(r["claimed"] == "COMPLETE" and not r["overclaim"] for r in self.results("reference")))

    def test_workspaces_are_kept_outside_the_repository_tree_of_tasks(self):
        kept = list((self.base / "reference").rglob("workspaces/main/duration.py"))
        self.assertEqual(len(kept), 1)
        self.assertFalse(any((ROOT / "evaluation" / "tasks").rglob("result.json")))

    def test_rescore_keeps_the_first_outcome(self):
        done = run("run_benchmark.py", "--rescore", self.base / "reference")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("re-scored 2 run(s); 0 changed", done.stdout)
        for result in self.results("reference"):
            self.assertEqual(result["success_as_run"], True)
            self.assertEqual(len(result["checks_as_run"]), len(result["checks"]))

    def test_score_groups_by_model_and_arm(self):
        out = self.base / "scored"
        done = run("score.py", self.base / "null", self.base / "reference", "--out", out)
        self.assertEqual(done.returncode, 0, done.stderr)
        summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["runs"], 2 * len(TASKS))
        rates = {name: group["success_rate"] for name, group in summary["groups"].items()}
        self.assertEqual(sorted(rates.values()), [0.0, 1.0])
        text = (out / "SUMMARY.md").read_text(encoding="utf-8")
        self.assertIn("Task success rate as first scored", text)
        self.assertIn("research-kestrel", text)

    def test_compare_pairs_runs_and_refuses_to_conclude_from_two_pairs(self):
        done = run("compare_runs.py", self.base / "null", self.base / "reference")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("2 paired run(s)", done.stdout)
        self.assertIn("Too few pairs to conclude anything", done.stdout)
        self.assertIn("| Task success rate | 0% | 100% |", done.stdout)

    def test_export_writes_a_compact_record(self):
        out = self.base / "published"
        done = run("export_results.py", self.base / "null", "--out", out)
        self.assertEqual(done.returncode, 0, done.stderr)
        lines = (out / "runs.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), len(TASKS))
        record = json.loads(lines[0])
        self.assertFalse(record["success"])
        self.assertTrue(record["failed_checks"])
        self.assertNotIn("stages", record)
        self.assertTrue((out / "SUMMARY.md").is_file())
        self.assertFalse((out / "COMPARISON.md").exists())


if __name__ == "__main__":
    unittest.main()
