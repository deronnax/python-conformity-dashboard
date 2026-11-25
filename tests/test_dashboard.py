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
    {"id": "cpython", "name": "CPython", "version": "3.12.15 (main) [Clang]",
     "threads": {"workers": 4, "cores": 4, "sequential": 1.0, "parallel": 1.02, "speedup": 0.98, "gil": None}},
    {"id": "pypy", "name": "PyPy", "version": "3.12.15 (abc)\n[PyPy 8.0.1 with GCC]",
     "threads": {"status": "timeout", "detail": "The process exceeded 120 seconds."}},
]


def passed(detail=""):
    return {"status": "passed", "detail": detail}


def report(**overrides):
    base = {
        "generatedAt": "2026-11-25T14:58:13+00:00",
        "platform": "Linux 7.0 · x86_64",
        "reference": "3.12.15",
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
            "query": "", "tags": {"pypy": {"interpreter": "pp312", "abi": "pypy312_pp80", "platform": "linux"}},
            "items": [{
                "project": "lxml", "downloads": 551075, "version": "6.1.3", "module": "lxml.etree",
                "outcomes": {"cpython": passed(),
                             "pypy": {"status": "otherAbi", "detail": "Wheels published for pypy312_pp73."}},
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
        self.assertEqual(saved["reference"], "3.12.15")
        for language, page in pages.items():
            for anchor in ("pypi-packages", "applications", "shared-cases", "cpython-tests", "interpreters", "history"):
                self.assertIn(f'id="{anchor}"', page)
                self.assertIn(f'href="#{anchor}"', page)
            self.assertIn(TRANSLATIONS[language]["statuses"]["otherAbi"], page)
            self.assertIn(TRANSLATIONS[language]["applicationTitles"]["numpy-array"], page)
            self.assertIn('<span class="runtime-note">pypy312_pp80</span>', page)
            self.assertNotIn("$", page.replace("$ ", ""), "unsubstituted template field")
        self.assertIn("<pre>Returns None</pre>", pages["en"])
        self.assertIn("<pre>Lève BufferError</pre>", pages["fr"])
        self.assertIn("<pre>charge pp80</pre>", pages["fr"])

    def test_accepts_reports_without_optional_measurements(self):
        legacy = report(applications=[], packages=None)
        pages, _ = render(legacy)
        self.assertIn(TRANSLATIONS["en"]["applicationsEmpty"], pages["en"])
        self.assertIn(TRANSLATIONS["fr"]["packagesEmpty"], pages["fr"])

    def test_a_performance_only_runtime_is_absent_from_conformity_views(self):
        data = report()
        data["runtimes"].append({"id": "rustpython", "name": "RustPython", "version": "3.14.0 (RustPython 0.6.0)",
                                 "threads": {"workers": 4, "cores": 4, "sequential": 1.0, "parallel": 0.6,
                                             "speedup": 1.69, "gil": False}})
        data["benchmarks"] = [benchmark_row(cpython=1.0, pypy=0.2, rustpython=3.3)]
        pages, _ = render(data)
        for language in ("en", "fr"):
            page = pages[language]
            for view in ("shared-cases", "applications", "pypi-packages"):
                panel = page.split(f'<section id="{view}"')[1].split("</section>")[0]
                self.assertNotIn("RustPython", panel.split("<table", 1)[1])
                self.assertIn(TRANSLATIONS[language]["performanceOnly"], panel)
            performance = page.split('<section id="performance"')[1].split("</section>")[0]
            self.assertIn("RustPython", performance)

    def test_accepts_package_reports_without_wheel_tags(self):
        data = report()
        del data["packages"]["tags"]
        pages, _ = render(data)
        self.assertNotIn("runtime-note", pages["en"])


class ContractAndVersionTests(unittest.TestCase):
    def data(self):
        data = report()
        row = data["common"][0]
        row.update(contract="cpython_behavior", contractSource=None, source=None, sourceTest=None)
        data["common"].append(dict(row, id="json-empty", module="json", api="json.loads",
                                   contract="stdlib_spec",
                                   contractSource="https://docs.python.org/3.12/library/json.html#json.loads",
                                   source="https://example.test/test_json.py", sourceTest="test.test_json.Demo.test_empty"))
        data["runtimes"].append({"id": "freethreaded", "name": "CPython 3.14t", "version": "3.14.9 free-threading build",
                                 "language": "3.14.9", "implementationVersion": "3.14.9"})
        for row in data["common"]:
            row["outcomes"]["freethreaded"] = passed()
        return data

    def test_cases_show_their_contract_and_provenance(self):
        pages, saved = render(self.data())
        for language in ("en", "fr"):
            copy = TRANSLATIONS[language]
            page = pages[language]
            self.assertIn(copy["contracts"]["cpython_behavior"], page)
            self.assertIn('<a href="https://docs.python.org/3.12/library/json.html#json.loads">', page)
            self.assertIn(copy["upstreamNone"], page)
            self.assertIn(copy["upstreamSame"], page)
            self.assertIn('data-contract="stdlib_spec"', page)
            self.assertIn("<select data-contract-filter>", page)
        self.assertEqual(saved["common"][0]["contract"], "cpython_behavior")

    def test_cross_version_runtimes_are_labelled(self):
        pages, _ = render(self.data())
        note = TRANSLATIONS["en"]["crossVersionNote"].format(version="3.14")
        self.assertIn(f'<span class="runtime-note">{note}</span>', pages["en"])
        card = TRANSLATIONS["fr"]["crossVersionCard"].format(version="3.14.9", reference="3.12.15")
        self.assertIn(card, pages["fr"].replace("&#x27;", "'"))

    def test_the_interpreters_view_separates_release_and_language(self):
        data = report()
        data["runtimes"][1].update(language="3.12.15", implementationVersion="8.0.1")
        pages, _ = render(data)
        self.assertIn(">8.0.1</td>", pages["en"])
        self.assertIn(TRANSLATIONS["en"]["implementationVersion"], pages["en"])

    def test_reports_without_version_fields_still_render(self):
        pages, _ = render(report())
        self.assertIn(">8.0.1</td>", pages["en"])
        self.assertNotIn("data-contract-filter", pages["en"])
        self.assertNotIn(TRANSLATIONS["en"]["performanceOnly"], pages["en"])


class VersionSwitchTests(unittest.TestCase):
    def render(self, current):
        site = {"current": current, "versions": [("3.12", ""), ("3.11", "3.11/")]}
        with TemporaryDirectory() as directory:
            generate(report(), Path(directory), (), site=site)
            return {language: (Path(directory) / path).read_text(encoding="utf-8")
                    for language, path in (("en", "index.html"), ("fr", "fr/index.html"))}

    def test_links_reach_the_same_language_of_every_version(self):
        root = self.render("3.12")
        self.assertIn('href="index.html" data-version-link aria-current="page">Python 3.12', root["en"])
        self.assertIn('href="3.11/index.html" data-version-link>Python 3.11', root["en"])
        self.assertIn('href="../3.11/fr/index.html" data-version-link>Python 3.11', root["fr"])
        nested = self.render("3.11")
        self.assertIn('href="../index.html" data-version-link>Python 3.12', nested["en"])
        self.assertIn('href="../../fr/index.html" data-version-link>Python 3.12', nested["fr"])
        self.assertIn('href="../3.11/index.html" data-version-link aria-current="page">Python 3.11', nested["en"])

    def test_a_single_version_has_no_switch(self):
        pages, _ = render(report())
        self.assertNotIn("data-version-link", pages["en"])


class InterpreterTests(unittest.TestCase):
    def test_shows_thread_scaling_and_failed_measurements(self):
        pages, _ = render(report())
        self.assertIn('<progress max="4" value="0.98"', pages["en"])
        self.assertIn("×0.98", pages["en"])
        self.assertIn(TRANSLATIONS["en"]["gilUnknown"], pages["en"])
        self.assertIn(TRANSLATIONS["fr"]["statuses"]["timeout"], pages["fr"])
        self.assertIn("<code>pypy312_pp80</code>", pages["en"])

    def test_reports_the_gil_state_when_the_interpreter_names_it(self):
        data = report()
        data["runtimes"][0]["threads"].update(gil=False, speedup=3.7)
        pages, _ = render(data)
        self.assertIn(TRANSLATIONS["en"]["gilDisabled"], pages["en"])
        self.assertIn(TRANSLATIONS["fr"]["gilDisabled"], pages["fr"])


def benchmark_row(**medians):
    outcomes = {}
    for key, median in medians.items():
        outcomes[key] = ({"status": "passed", "detail": "", "median": median, "min": median, "stdev": 0.0,
                          "rounds": 5, "first": median * 2} if isinstance(median, float) else median)
    return {"id": "nbody", "title": "N-body simulation", "titleFr": "Simulation à N corps", "outcomes": outcomes}


class PerformancePageTests(unittest.TestCase):
    def page(self, rows, language="en"):
        pages, _ = render(report(benchmarks=rows))
        return pages[language]

    def test_shows_times_ratios_and_the_geometric_mean(self):
        page = self.page([benchmark_row(cpython=2.0, pypy=0.5)])
        self.assertIn('<span class="time">2 s</span><span class="ratio same">reference</span>', page)
        self.assertIn('<span class="time">0.5 s</span><span class="ratio faster">4.0× faster</span>', page)
        self.assertIn("×4", page)
        self.assertIn("5 timed rounds", page)

    def test_slower_results_and_french_decimals(self):
        page = self.page([benchmark_row(cpython=1.0, pypy=2.5)], "fr")
        self.assertIn('<span class="ratio slower">2,5 fois plus lent</span>', page)
        self.assertIn('<span class="time">2,5 s</span>', page)

    def test_failed_benchmarks_show_their_status(self):
        page = self.page([benchmark_row(cpython=1.0, pypy={"status": "different", "detail": "Expected: 1"})])
        self.assertIn('<span class="status different">Different</span>', page)

    def test_a_report_without_benchmarks_says_so(self):
        self.assertIn(TRANSLATIONS["en"]["performanceEmpty"], self.page([]))

    def test_the_speed_chart_uses_a_logarithmic_scale(self):
        earlier = snapshot(report(generatedAt="2026-11-18T05:00:00+00:00",
                                  benchmarks=[benchmark_row(cpython=1.0, pypy=0.01)]))
        pages, _ = render(report(benchmarks=[benchmark_row(cpython=1.0, pypy=0.05)]), [earlier])
        page = pages["en"]
        self.assertIn("Speed relative to CPython", page)
        # PyPy is 100 times faster at most, so the scale spans x1 to x100 with a tick per decade.
        for tick in ("×1", "×10", "×100"):
            self.assertIn(f">{tick}</text>", page)
        self.assertNotIn(">×0.1</text>", page)


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
