import json
import unittest
from pathlib import Path
from unittest import mock

import measure


def reply(status, detail=""):
    return json.dumps({"status": status, "detail": detail})


class UpstreamTests(unittest.TestCase):
    def run_upstream(self, answers, executables):
        def invoke(executable, script, tests, method, cwd):
            return answers[executable]
        with mock.patch.object(measure, "UPSTREAM", {"json": ("test.test_json.Demo.test_one",)}), \
                mock.patch.object(measure, "invoke", invoke):
            return measure.upstream_results(executables, Path("tests-root/test"), ".")[0]["outcomes"]

    def test_runs_on_every_interpreter_that_targets_the_reference_version(self):
        executables = {"cpython": "cpython", "pypy": "pypy", "graalpy": "graalpy", "rustpython": "rustpython"}
        answers = {name: reply("passed") for name in executables}
        outcomes = self.run_upstream(answers, executables)
        self.assertEqual(set(outcomes), {"cpython", "pypy", "graalpy"})

    def test_a_failing_reference_makes_the_other_results_unverified(self):
        executables = {"cpython": "cpython", "pypy": "pypy", "graalpy": "graalpy"}
        answers = {"cpython": reply("error", "boom"), "pypy": reply("passed"), "graalpy": reply("different", "x")}
        outcomes = self.run_upstream(answers, executables)
        self.assertEqual(outcomes["cpython"]["status"], "error")
        self.assertEqual(outcomes["pypy"]["status"], "unverified")
        self.assertEqual(outcomes["graalpy"]["status"], "unverified")

    def test_works_without_graalpy(self):
        executables = {"cpython": "cpython", "pypy": "pypy"}
        outcomes = self.run_upstream({"cpython": reply("passed"), "pypy": reply("different", "x")}, executables)
        self.assertEqual(outcomes["pypy"]["status"], "different")
        self.assertNotIn("graalpy", outcomes)


if __name__ == "__main__":
    unittest.main()
