import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import test_suites


def raw(runtime, tests, tracebacks=None, status="completed"):
    return {"suite": "django", "project": "Django", "version": "5.2.19", "runtime": runtime, "status": status,
            "duration": 90, "detail": "", "tests": tests, "tracebacks": tracebacks or {}}


class OutcomeTests(unittest.TestCase):
    def test_the_most_severe_outcome_of_a_test_is_kept(self):
        with TemporaryDirectory() as directory:
            path = Path(directory, "results.jsonl")
            lines = [{"id": "a.T.test", "status": "failure", "traceback": "AssertionError: 1 != 2"},
                     {"id": "a.T.test", "status": "error", "traceback": "TypeError: boom"},
                     {"id": "a.T.other", "status": "passed"}]
            path.write_text("\n".join(map(json.dumps, lines)) + "\n{truncated", encoding="utf-8")
            tests, tracebacks = test_suites.read_outcomes(path)
        self.assertEqual(tests, {"a.T.test": "error", "a.T.other": "passed"})
        self.assertEqual(tracebacks["a.T.test"], "TypeError: boom")

    def test_reads_the_app_of_a_test_and_of_a_class_setup(self):
        self.assertEqual(test_suites.app("queries.tests.Queries1Tests.test_ticket"), "queries")
        self.assertEqual(test_suites.app("setUpClass (file_storage.tests.FileLikeObjectTestCase)"), "file_storage")

    def test_the_message_is_the_last_line_without_addresses(self):
        self.assertEqual(test_suites.message("Traceback\n  File x\nTypeError: <obj at 0x7f00ab>\n"),
                         "TypeError: <obj at 0x…>")


class SummaryTests(unittest.TestCase):
    def test_counts_tests_that_pass_on_cpython_only(self):
        cpython = raw("cpython", {"a.T.one": "passed", "a.T.two": "passed", "b.T.three": "failure", "b.T.four": "passed"},
                      {"b.T.three": "AssertionError: machine"})
        pypy = raw("pypy", {"a.T.one": "error", "a.T.two": "error", "b.T.three": "failure"},
                   {"a.T.one": "TypeError: boom", "a.T.two": "TypeError: boom", "b.T.three": "AssertionError: machine"})
        summary = test_suites.summarize({"cpython": cpython, "pypy": pypy})
        outcome = summary["outcomes"]["pypy"]
        self.assertEqual(summary["tests"], 4)
        self.assertEqual((outcome["differences"], outcome["notRun"]), (2, 1))
        self.assertEqual(outcome["groups"], [{"app": "a", "status": "error", "message": "TypeError: boom", "count": 2,
                                              "examples": ["a.T.one", "a.T.two"], "traceback": "TypeError: boom"}])
        self.assertEqual(summary["outcomes"]["cpython"]["groups"][0]["message"], "AssertionError: machine")

    def test_no_comparison_without_a_completed_cpython_run(self):
        summary = test_suites.summarize({"cpython": raw("cpython", {}, status="timeout"),
                                         "pypy": raw("pypy", {"a.T.one": "error"})})
        self.assertNotIn("differences", summary["outcomes"]["pypy"])

    def test_only_the_largest_groups_are_kept(self):
        tests = {f"app{index}.T.test": "error" for index in range(test_suites.GROUP_LIMIT + 5)}
        tests["app0.T.second"] = "error"
        cpython = raw("cpython", dict.fromkeys(tests, "passed"))
        summary = test_suites.summarize({"cpython": cpython, "pypy": raw("pypy", tests)})
        outcome = summary["outcomes"]["pypy"]
        self.assertEqual(len(outcome["groups"]), test_suites.GROUP_LIMIT)
        self.assertEqual(outcome["groups"][0]["count"], 2)
        self.assertEqual((outcome["hiddenGroups"], outcome["hiddenTests"]), (5, 5))

    def test_loads_the_runs_of_one_version(self):
        with TemporaryDirectory() as directory:
            for name, runtime in (("suite-3.12-cpython", "cpython"), ("suite-3.12-pypy", "pypy"), ("suite-3.11-pypy", "pypy")):
                Path(directory, name).mkdir()
                Path(directory, name, "suite.json").write_text(json.dumps(raw(runtime, {"a.T.one": "passed"})))
            suites = test_suites.load(directory, "3.12")
        self.assertEqual(list(suites[0]["outcomes"]), ["cpython", "pypy"])
        self.assertEqual(test_suites.load(directory, "3.13"), [])
