import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "notes.py"


class NotesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_notes(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.tmp.name, capture_output=True, text=True)

    def out(self, *args):
        done = self.run_notes(*args)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    # M1
    def test_add_prints_incrementing_ids(self):
        self.assertEqual(self.out("add", "first"), "Added note 1\n")
        self.assertEqual(self.out("add", "second", "--tag", "b", "--tag", "a"), "Added note 2\n")

    def test_list_format_and_order(self):
        self.out("add", "first")
        self.out("add", "second", "--tag", "b", "--tag", "a")
        self.assertEqual(self.out("list"), "1\tfirst\t\n2\tsecond\ta,b\n")

    def test_list_empty(self):
        self.assertEqual(self.out("list"), "")

    def test_notes_are_persisted(self):
        self.out("add", "kept")
        self.assertTrue((Path(self.tmp.name) / "notes.json").is_file())
        self.assertEqual(self.out("list"), "1\tkept\t\n")

    # M2
    def test_delete(self):
        self.out("add", "a")
        self.out("add", "b")
        self.assertEqual(self.out("delete", "1"), "Deleted note 1\n")
        self.assertEqual(self.out("list"), "2\tb\t\n")

    def test_delete_unknown_id(self):
        done = self.run_notes("delete", "7")
        self.assertEqual(done.returncode, 1)
        self.assertEqual(done.stderr, "Error: note 7 not found\n")

    def test_ids_are_never_reused(self):
        self.out("add", "a")
        self.out("add", "b")
        self.out("delete", "2")
        self.assertEqual(self.out("add", "c"), "Added note 3\n")

    # M3
    def test_search_ignores_case(self):
        self.out("add", "Buy MILK")
        self.out("add", "call mum")
        self.assertEqual(self.out("search", "milk"), "1\tBuy MILK\t\n")

    def test_list_filters_by_exact_tag(self):
        self.out("add", "a", "--tag", "home")
        self.out("add", "b", "--tag", "Home")
        self.out("add", "c", "--tag", "homework")
        self.assertEqual(self.out("list", "--tag", "home"), "1\ta\thome\n")

    # M4
    def test_export_markdown(self):
        self.out("add", "plain")
        self.out("add", "tagged", "--tag", "z", "--tag", "a")
        self.assertEqual(self.out("export", "--format", "md"), "# Notes\n\n- [1] plain\n- [2] tagged (tags: a, z)\n")

    def test_export_json(self):
        self.out("add", "tagged", "--tag", "z", "--tag", "a")
        self.assertEqual(json.loads(self.out("export", "--format", "json")), [{"id": 1, "text": "tagged", "tags": ["a", "z"]}])

    def test_export_to_file(self):
        self.out("add", "one")
        self.assertEqual(self.out("export", "--format", "md", "--output", "out.md"), "Exported 1 notes to out.md\n")
        self.assertEqual((Path(self.tmp.name) / "out.md").read_text(), "# Notes\n\n- [1] one\n")

    def test_export_rejects_unknown_format(self):
        self.assertEqual(self.run_notes("export", "--format", "xml").returncode, 2)

    # Always
    def test_corrupted_store(self):
        store = Path(self.tmp.name) / "notes.json"
        store.write_text("{not json")
        for command in (["list"], ["add", "x"], ["delete", "1"], ["search", "x"], ["export", "--format", "md"]):
            done = self.run_notes(*command)
            self.assertEqual(done.returncode, 1, command)
            self.assertEqual(done.stderr, "Error: notes.json is corrupted\n")
        self.assertEqual(store.read_text(), "{not json")


if __name__ == "__main__":
    unittest.main()
