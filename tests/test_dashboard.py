import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dashboard import describe_observation, generate
from dashboard_content import TRANSLATIONS
from history import load as _load, merge, snapshot


def load_entries(path):
    return _load(path)


def published_history(data, previous=()):
    """Return the entries of the history.json that generate() publishes."""
    with TemporaryDirectory() as directory:
        generate(data, Path(directory), previous)
        return _load(Path(directory) / "history.json")


RUNTIMES = [
    {"id": "cpython", "name": "CPython", "version": "3.11.17 (main) [Clang]",
     "threads": {"workers": 4, "cores": 4, "sequential": 1.0, "parallel": 1.02, "speedup": 0.98, "gil": None}},
    {"id": "pypy", "name": "PyPy", "version": "3.11.17 (abc)\n[PyPy 8.0.1 with GCC]",
     "threads": {"status": "timeout", "detail": "The process exceeded 120 seconds."}},
]


def passed(detail=""):
    return {"status": "passed", "detail": detail}


def report(**overrides):
    base = {
        "generatedAt": "2026-11-25T14:58:13+00:00",
        "platform": "Linux 7.0 · x86_64",
        "reference": "3.11.17",
        "runtimes": copy.deepcopy(RUNTIMES),
        "common": [{
            "id": "mmap-memoryview", "module": "mmap", "api": "mmap.mmap",
            "title": "Reject closing a map with an active memory view", "titleFr": "Refuser la fermeture",
            "code": "import mmap", "source": "https://example.test/test_mmap.py",
            "sourceTest": "test.test_mmap.MmapTests.test_context_manager",
            "outcomes": {"cpython": passed("exception: BufferError"),
                         "pypy": {"status": "different", "detail": "NoneType: None"}},
        }],
        "upstream": [{
            "id": "test.test_json.Test.test_empty", "module": "json", "title": "test_empty",
            "source": "https://example.test/test_json.py", "sourceTest": "test.test_json.Test.test_empty",
            "outcomes": {"cpython": passed(), "pypy": passed()},
        }],
        "applications": [{
            "id": "numpy-array", "package": "NumPy", "version": "2.4.4",
            "outcomes": {"cpython": passed(),
                         "pypy": {"status": "otherAbi", "detail": "loads pp80", "detailFr": "charge pp80"}},
        }],
        "packages": {
            "start": "2026-10-26", "end": "2026-11-25", "source": "https://github.com/ClickHouse/clickpy",
            "query": "", "tags": {"pypy": {"interpreter": "pp311", "abi": "pypy311_pp80", "platform": "linux"}},
            "items": [{
                "project": "lxml", "downloads": 551075, "version": "6.1.3", "module": "lxml.etree",
                "outcomes": {"cpython": passed(),
                             "pypy": {"status": "otherAbi", "detail": "Wheels published for pypy311_pp73."}},
            }],
        },
    }
    base.update(overrides)
    return base


def render(data, previous=()):
    with TemporaryDirectory() as directory:
        output = Path(directory)
        generate(data, output, previous)
        pages = {language: (output / path).read_text(encoding="utf-8")
                 for language, path in (("en", "index.html"), ("fr", "fr/index.html"))}
        saved = json.loads((output / "results.json").read_text(encoding="utf-8"))
    return pages, saved


class GenerateTests(unittest.TestCase):
    def test_renders_every_view_in_both_languages(self):
        pages, saved = render(report())
        self.assertEqual(saved["reference"], "3.11.17")
        for language, page in pages.items():
            for anchor in ("pypi-packages", "applications", "shared-cases", "cpython-tests", "interpreters", "history"):
                self.assertIn(f'id="{anchor}"', page)
                self.assertIn(f'href="#{anchor}"', page)
            self.assertIn(TRANSLATIONS[language]["statuses"]["otherAbi"], page)
            self.assertIn(TRANSLATIONS[language]["applicationTitles"]["numpy-array"], page)
            self.assertIn('<span class="runtime-note">pypy311_pp80</span>', page)
            self.assertNotIn("$", page.replace("$ ", ""), "unsubstituted template field")
        self.assertIn("<pre>Returns None</pre>", pages["en"])
        self.assertIn("<pre>Lève BufferError</pre>", pages["fr"])
        self.assertIn("<pre>charge pp80</pre>", pages["fr"])

    def test_accepts_reports_without_optional_measurements(self):
        legacy = report(applications=[], packages=None)
        pages, _ = render(legacy)
        self.assertIn(TRANSLATIONS["en"]["applicationsEmpty"], pages["en"])
        self.assertIn(TRANSLATIONS["fr"]["packagesEmpty"], pages["fr"])

    def test_accepts_package_reports_without_wheel_tags(self):
        data = report()
        del data["packages"]["tags"]
        pages, _ = render(data)
        self.assertNotIn("runtime-note", pages["en"])


class InterpreterTests(unittest.TestCase):
    def test_shows_thread_scaling_and_failed_measurements(self):
        pages, _ = render(report())
        self.assertIn('<progress max="4" value="0.98"', pages["en"])
        self.assertIn("×0.98", pages["en"])
        self.assertIn(TRANSLATIONS["en"]["gilUnknown"], pages["en"])
        self.assertIn(TRANSLATIONS["fr"]["statuses"]["timeout"], pages["fr"])
        self.assertIn("<code>pypy311_pp80</code>", pages["en"])

    def test_reports_the_gil_state_when_the_interpreter_names_it(self):
        data = report()
        data["runtimes"][0]["threads"].update(gil=False, speedup=3.7)
        pages, _ = render(data)
        self.assertIn(TRANSLATIONS["en"]["gilDisabled"], pages["en"])
        self.assertIn(TRANSLATIONS["fr"]["gilDisabled"], pages["fr"])


class HistoryPageTests(unittest.TestCase):
    def later(self, stamp, **extra):
        data = report(generatedAt=stamp, **extra)
        return data

    def previous(self, *stamps):
        entries = []
        for stamp in stamps:
            entries = merge(entries, snapshot(self.later(stamp)))
        return entries

    def test_a_single_run_explains_how_the_history_grows(self):
        pages, saved = render(report())
        self.assertIn(TRANSLATIONS["en"]["historyFirst"], pages["en"])
        self.assertIn("<circle", pages["en"])
        self.assertNotIn("<polyline", pages["en"])

    def test_several_runs_draw_lines_and_a_table_view(self):
        pages, _ = render(report(), self.previous("2026-11-11T05:00:00+00:00", "2026-11-18T05:00:00+00:00"))
        self.assertNotIn(TRANSLATIONS["en"]["historyFirst"], pages["en"])
        self.assertIn("<polyline", pages["en"])
        for day in ("2026-11-11", "2026-11-18", "2026-11-25"):
            self.assertIn(f"<th scope=\"row\">{day}</th>", pages["en"])
        self.assertIn(TRANSLATIONS["fr"]["historyTable"], pages["fr"])

    def test_the_published_history_contains_every_run_once(self):
        first = published_history(report(generatedAt="2026-11-11T05:00:00+00:00"))
        again = published_history(report(), first)
        self.assertEqual([item["generatedAt"] for item in again],
                         ["2026-11-11T05:00:00+00:00", "2026-11-25T14:58:13+00:00"])


class HistoryModuleTests(unittest.TestCase):
    def test_snapshot_counts_statuses_per_runtime(self):
        entry = snapshot(report())
        self.assertEqual(entry["suites"]["packages"]["total"], 1)
        self.assertEqual(entry["suites"]["packages"]["runtimes"]["pypy"], {"otherAbi": 1})
        self.assertEqual(entry["suites"]["common"]["runtimes"]["cpython"], {"passed": 1})
        self.assertEqual(entry["runtimes"]["cpython"]["speedup"], 0.98)
        self.assertIsNone(entry["runtimes"]["pypy"]["speedup"])

    def test_merge_replaces_a_rerun_and_stays_sorted(self):
        first, second = {"generatedAt": "2026-11-02"}, {"generatedAt": "2026-11-09"}
        merged = merge([second, first], {"generatedAt": "2026-11-09", "again": True})
        self.assertEqual([item["generatedAt"] for item in merged], ["2026-11-02", "2026-11-09"])
        self.assertTrue(merged[1]["again"])

    def test_unreadable_history_starts_a_new_one(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            self.assertEqual(load_entries(path), [])
            path.write_text("<html>404</html>", encoding="utf-8")
            self.assertEqual(load_entries(path), [])
            path.write_text(json.dumps({"version": 99, "entries": [{"generatedAt": "x"}]}), encoding="utf-8")
            self.assertEqual(load_entries(path), [])


class ObservationTests(unittest.TestCase):
    def describe(self, status, detail, language="en"):
        return describe_observation({"status": status, "detail": detail}, language, TRANSLATIONS[language])

    def test_phrases_values_and_exceptions(self):
        self.assertEqual(self.describe("passed", "int: 6"), "Returns 6 (int)")
        self.assertEqual(self.describe("passed", "exception: ValueError"), "Raises ValueError")
        self.assertEqual(self.describe("different", "unexpected exception: AttributeError"),
                         "Raises an unexpected AttributeError")
        self.assertEqual(self.describe("different", "NoneType: None", "fr"), "Renvoie None")

    def test_leaves_measurement_problems_unchanged(self):
        detail = "Expected by the corpus: int: 6\nObserved: int: 7"
        self.assertEqual(self.describe("unverified", detail), detail)
        self.assertEqual(self.describe("missing", "sqlite3 No module named '_sqlite3'"),
                         "sqlite3 No module named '_sqlite3'")


if __name__ == "__main__":
    unittest.main()
