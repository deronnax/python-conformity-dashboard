import unittest
from unittest import mock

import benchmarks
import measure
import performance


def timed(status="passed", median=1.0):
    return {"status": status, "detail": "", "median": median}


class SpeedTests(unittest.TestCase):
    def row(self, **medians):
        return {"outcomes": {key: timed(median=value) if isinstance(value, float) else value
                             for key, value in medians.items()}}

    def test_speedup_is_the_reference_time_over_the_measured_time(self):
        row = self.row(cpython=2.0, pypy=0.5)
        self.assertEqual(performance.speedup(row, "pypy"), 4.0)
        self.assertEqual(performance.speedup(row, "cpython"), 1.0)

    def test_unmeasured_benchmarks_have_no_speedup(self):
        row = self.row(cpython=1.0, pypy={"status": "different", "detail": "x"})
        self.assertIsNone(performance.speedup(row, "pypy"))
        self.assertIsNone(performance.speedup(row, "missing"))
        self.assertIsNone(performance.speedup(self.row(cpython={"status": "timeout", "detail": ""}, pypy=1.0), "pypy"))

    def test_geometric_mean_counts_only_measured_benchmarks(self):
        rows = [self.row(cpython=1.0, pypy=0.25), self.row(cpython=1.0, pypy=1.0),
                self.row(cpython=1.0, pypy={"status": "timeout", "detail": ""})]
        mean, count = performance.geometric_means(rows, ["pypy"])["pypy"]
        self.assertAlmostEqual(mean, 2.0)
        self.assertEqual(count, 2)

    def test_summarize_reports_spread(self):
        summary = performance.summarize([1.0, 2.0, 3.0])
        self.assertEqual((summary["median"], summary["min"], summary["rounds"]), (2.0, 1.0, 3))
        self.assertEqual(performance.summarize([1.0])["stdev"], 0.0)


class KernelTests(unittest.TestCase):
    """Published results of the Computer Language Benchmarks Game programs."""

    def test_fannkuch(self):
        self.assertEqual(benchmarks.fannkuch_once(7), "228 16")
        self.assertEqual(benchmarks.fannkuch(7, repeat=2), "228 16")

    def test_nbody_conserves_the_published_energy(self):
        self.assertEqual(benchmarks.nbody(1000), "-0.169087605")

    def test_spectral_norm(self):
        self.assertEqual(benchmarks.spectral_norm(100), "1.274219991")

    def test_queens(self):
        self.assertEqual(benchmarks.queens(8), "92")

    def test_generated_inputs_are_deterministic(self):
        first = [value for _, value in zip(range(5), benchmarks.lcg(7))]
        self.assertEqual(first, [value for _, value in zip(range(5), benchmarks.lcg(7))])
        self.assertGreater(len(set(first)), 4)

    def test_every_benchmark_has_a_title(self):
        for name, (function, title) in benchmarks.BENCHMARKS.items():
            self.assertTrue(callable(function) and title, name)


class BenchmarkResultsTests(unittest.TestCase):
    def observe(self, answers):
        """Return an invoke() replacement that serves canned observations per interpreter."""
        def invoke(executable, script, name, cwd, timeout):
            return answers[executable]
        return invoke

    def run_measure(self, answers):
        executables = {"cpython": "cpython", "pypy": "pypy"}
        with mock.patch.object(measure, "BENCHMARKS", {"demo": (None, "Demo")}), \
                mock.patch.object(measure, "invoke", self.observe(answers)):
            return measure.benchmark_results(executables, ".")[0]["outcomes"]

    def finished(self, result="42", samples=(1.0, 2.0, 3.0)):
        import json
        return json.dumps({"result": result, "first": 1.5, "samples": list(samples)})

    def test_matching_answers_become_timings(self):
        outcomes = self.run_measure({"cpython": self.finished(), "pypy": self.finished(samples=(0.1, 0.1, 0.1))})
        self.assertEqual(outcomes["pypy"]["status"], "passed")
        self.assertEqual((outcomes["cpython"]["median"], outcomes["pypy"]["median"]), (2.0, 0.1))
        self.assertEqual(outcomes["cpython"]["first"], 1.5)

    def test_a_wrong_answer_is_a_difference_not_a_time(self):
        outcomes = self.run_measure({"cpython": self.finished(), "pypy": self.finished(result="43")})
        self.assertEqual(outcomes["pypy"]["status"], "different")
        self.assertNotIn("median", outcomes["pypy"])
        self.assertIn("Expected: 42", outcomes["pypy"]["detail"])

    def test_failures_keep_their_status(self):
        outcomes = self.run_measure({"cpython": self.finished(),
                                     "pypy": {"status": "timeout", "detail": "The process exceeded 240 seconds."}})
        self.assertEqual(outcomes["pypy"]["status"], "timeout")

    def test_a_failed_reference_invalidates_the_other_timings(self):
        outcomes = self.run_measure({"cpython": {"status": "crash", "detail": "boom"}, "pypy": self.finished()})
        self.assertEqual(outcomes["cpython"]["status"], "crash")
        self.assertEqual(outcomes["pypy"]["status"], "unverified")


if __name__ == "__main__":
    unittest.main()
