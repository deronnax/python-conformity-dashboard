import copy
import json
from html import escape
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dashboard import describe_observation, generate
from dashboard_content import COPY
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
            "code": "def numpy_array():\n    import numpy as np\n",
            "outcomes": {"cpython": passed(),
                         "pypy": {"status": "otherAbi", "detail": "loads pp80"}},
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
        pages = {"en": (output / "index.html").read_text(encoding="utf-8"),
                 "fr": (output / "fr" / "index.html").read_text(encoding="utf-8")}
        saved = json.loads((output / "results.json").read_text(encoding="utf-8"))
    return pages, saved


class GenerateTests(unittest.TestCase):
    def test_renders_every_view(self):
        pages, saved = render(report())
        self.assertEqual(saved["reference"], "3.12.15")
        for page in (pages["en"],):
            for anchor in ("pypi-packages", "applications", "shared-cases", "cpython-tests", "interpreters", "history"):
                self.assertIn(f'id="{anchor}"', page)
                self.assertIn(f'href="#{anchor}"', page)
            self.assertIn(COPY["statuses"]["otherAbi"], page)
            self.assertIn(COPY["applicationTitles"]["numpy-array"], page)
            self.assertIn('<span class="runtime-note">pypy312_pp80</span>', page)
            self.assertNotIn("$", page.replace("$ ", ""), "unsubstituted template field")
        self.assertIn("<pre>Returns None</pre>", pages["en"])
        self.assertIn("<pre>loads pp80</pre>", pages["en"])
        self.assertNotIn("lang=\"fr\"", pages["en"])

    def test_the_former_french_page_redirects_to_english(self):
        pages, _ = render(report())
        self.assertIn('location.replace("../" + location.search + location.hash)', pages["fr"])

    def test_shows_the_code_of_each_scenario(self):
        pages, _ = render(report())
        self.assertIn(f'<summary>{COPY["scenarioCode"]}</summary><pre>def numpy_array():', pages["en"])

    def test_accepts_reports_without_optional_measurements(self):
        legacy = report(applications=[], packages=None)
        pages, _ = render(legacy)
        self.assertIn(COPY["applicationsEmpty"], pages["en"])
        self.assertIn(COPY["packagesEmpty"], pages["en"])

    def test_rustpython_appears_in_every_view(self):
        data = report()
        data["runtimes"].append({"id": "rustpython", "name": "RustPython", "version": "3.14.0 (RustPython 0.6.0)",
                                 "language": "3.14.0a0", "implementationVersion": "0.6.0a0",
                                 "threads": {"workers": 4, "cores": 4, "sequential": 1.0, "parallel": 0.6,
                                             "speedup": 1.69, "gil": False}})
        for suite in ("common", "upstream", "applications"):
            for row in data[suite]:
                row["outcomes"]["rustpython"] = passed()
        data["packages"]["items"][0]["outcomes"]["rustpython"] = {"status": "nativeOnly", "detail": ""}
        data["benchmarks"] = [benchmark_row(cpython=1.0, pypy=0.2, rustpython=3.3)]
        pages, _ = render(data)
        for language in ("en",):
            page = pages[language]
            note = COPY["performanceOnly"]
            for view in ("pypi-packages", "shared-cases", "cpython-tests", "applications", "performance", "interpreters"):
                panel = page.split(f'<section id="{view}"')[1].split("</section>")[0]
                self.assertIn("RustPython", panel)
                self.assertEqual(note in panel, view == "pypi-packages")
            self.assertIn(COPY["statuses"]["nativeOnly"], page)

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
        for language in ("en",):
            copy = COPY
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
        note = COPY["crossVersionNote"].format(version="3.14")
        self.assertIn(f'<span class="runtime-note">{note}</span>', pages["en"])
        card = COPY["crossVersionCard"].format(version="3.14.9", reference="3.12.15")
        self.assertIn(card, pages["en"].replace("&#x27;", "'"))

    def test_the_interpreters_view_separates_release_and_language(self):
        data = report()
        data["runtimes"][1].update(language="3.12.15", implementationVersion="8.0.1")
        pages, _ = render(data)
        self.assertIn(">8.0.1</td>", pages["en"])
        self.assertIn(COPY["implementationVersion"], pages["en"])

    def test_reports_without_version_fields_still_render(self):
        pages, _ = render(report())
        self.assertIn(">8.0.1</td>", pages["en"])
        self.assertNotIn("data-contract-filter", pages["en"])
        self.assertNotIn(COPY["performanceOnly"], pages["en"])


class VersionSwitchTests(unittest.TestCase):
    def render(self, current):
        site = {"current": current, "versions": [("3.11", ""), ("3.12", "3.12/")]}
        with TemporaryDirectory() as directory:
            generate(report(), Path(directory), (), site=site)
            return (Path(directory) / "index.html").read_text(encoding="utf-8")

    def test_links_reach_every_version_oldest_first(self):
        root = self.render("3.11")
        self.assertIn('href="index.html" data-version-link aria-current="page">Python 3.11', root)
        self.assertIn('href="3.12/index.html" data-version-link>Python 3.12', root)
        self.assertLess(root.index(">Python 3.11<"), root.index(">Python 3.12<"))
        nested = self.render("3.12")
        self.assertIn('href="../index.html" data-version-link>Python 3.11', nested)
        self.assertIn('href="../3.12/index.html" data-version-link aria-current="page">Python 3.12', nested)

    def test_version_notes_are_shown_in_both_languages(self):
        pages, _ = render(report(notes=["pypyBeta"]))
        for language in ("en",):
            self.assertIn(f'<p class="version-warning">{escape(COPY["pypyBeta"])}</p>', pages[language])
        pages, _ = render(report())
        self.assertNotIn("version-warning", pages["en"])

    def test_a_single_version_has_no_switch(self):
        pages, _ = render(report())
        self.assertNotIn("data-version-link", pages["en"])


class BlockerTests(unittest.TestCase):
    def test_packages_blocked_by_a_dependency_name_it(self):
        data = report()
        item = data["packages"]["items"][0]
        item["outcomes"]["pypy"] = {"status": "dependency", "detail": "ERROR: No matching distribution found for rpds-py>=0.25.0",
                                    "blocker": {"name": "rpds-py", "requirement": "rpds-py>=0.25.0", "version": "2026.9.1",
                                                "cause": "otherAbi", "published": ["pypy312_pp73"]}}
        pages, _ = render(data)
        for language in ("en",):
            copy = COPY
            self.assertIn(copy["statuses"]["dependency"], pages[language])
            self.assertIn(copy["blockersTitle"], pages[language])
            self.assertIn(copy["blockerPublished"].format(name="rpds-py 2026.9.1", published="pypy312_pp73"),
                          pages[language].replace("&#x27;", "'"))
        self.assertIn('<span class="blocker">via <code>rpds-py</code></span>', pages["en"])

    def test_no_blockers_no_table(self):
        pages, _ = render(report())
        self.assertNotIn(COPY["blockersTitle"], pages["en"])


class DeepLinkTests(unittest.TestCase):
    def test_rows_have_stable_anchors_and_permalinks(self):
        pages, _ = render(report())
        page = pages["en"]
        for fragment in ("case-mmap-memoryview", "test-test.test_json.test.test_empty", "package-lxml",
                         "scenario-numpy-array"):
            self.assertIn(f'id="{fragment}"', page)
            self.assertIn(f'href="#{fragment}"', page)

    def test_cases_copy_a_standalone_reproduction(self):
        data = report()
        data["common"][0]["code"] = "import mmap\n\nregion = mmap.mmap(-1, 4)\nview = memoryview(region)\nregion.close()"
        pages, _ = render(data)
        script = ("# Python Conformity: mmap-memoryview\n# CPython 3.12.15: Raises BufferError\nimport mmap\n\n"
                  "region = mmap.mmap(-1, 4)\nview = memoryview(region)\nprint(repr(region.close()))\n")
        self.assertIn(f'data-copy="{escape(script)}"', pages["en"])

    def test_packages_copy_the_install_and_import_commands(self):
        pages, _ = render(report())
        command = 'python -m pip install --only-binary=:all: lxml==6.1.3\npython -c "import lxml.etree"\n'
        self.assertIn(f'data-copy="{escape(command)}"', pages["en"])
        self.assertIn(COPY["copyReproduction"], pages["en"])


class FunctionalCheckViewTests(unittest.TestCase):
    def test_import_only_and_functional_successes_differ(self):
        data = report()
        item = data["packages"]["items"][0]
        item["check"] = "import lxml.etree\nassert lxml.etree.fromstring('<a/>').tag == 'a'"
        item["outcomes"]["cpython"] = {"status": "passed", "detail": "", "level": "functional"}
        item["outcomes"]["pypy"] = {"status": "passed", "detail": "", "level": "import"}
        pages, _ = render(data)
        for language in ("en",):
            copy = COPY
            page = pages[language]
            self.assertIn(f'<span class="status passed import-only">{escape(copy["importOnly"])}</span>', page)
            self.assertIn(escape(copy["checkTitle"]), page)
            self.assertIn(escape(copy["checkLevels"].format(functional=1, imported=0)), page)
            self.assertIn(escape(copy["checkLevels"].format(functional=0, imported=1)), page)

    def test_a_failed_check_is_shown_with_its_traceback(self):
        data = report()
        data["packages"]["items"][0]["outcomes"]["pypy"] = {
            "status": "functionError", "detail": "AssertionError: wrong tag", "level": "functional"}
        pages, _ = render(data)
        self.assertIn(COPY["statuses"]["functionError"], pages["en"])
        self.assertIn("AssertionError: wrong tag", pages["en"])
        self.assertIn(escape(COPY["noCheck"]), pages["en"])


class InterpreterTests(unittest.TestCase):
    def test_shows_thread_scaling_and_failed_measurements(self):
        pages, _ = render(report())
        self.assertIn('<progress max="4" value="0.98"', pages["en"])
        self.assertIn("×0.98", pages["en"])
        self.assertIn(COPY["gilUnknown"], pages["en"])
        self.assertIn(COPY["statuses"]["timeout"], pages["en"])
        self.assertIn("<code>pypy312_pp80</code>", pages["en"])

    def test_reports_the_gil_state_when_the_interpreter_names_it(self):
        data = report()
        data["runtimes"][0]["threads"].update(gil=False, speedup=3.7)
        pages, _ = render(data)
        self.assertIn(COPY["gilDisabled"], pages["en"])
        self.assertIn(COPY["gilDisabled"], pages["en"])


def benchmark_row(**medians):
    outcomes = {}
    for key, median in medians.items():
        outcomes[key] = ({"status": "passed", "detail": "", "median": median, "min": median, "stdev": 0.0,
                          "rounds": 5, "first": median * 2} if isinstance(median, float) else median)
    return {"id": "nbody", "title": "N-body simulation", "titleFr": "Simulation à N corps", "outcomes": outcomes}


class PerformancePageTests(unittest.TestCase):
    def page(self, rows):
        pages, _ = render(report(benchmarks=rows))
        return pages["en"]

    def test_shows_times_ratios_and_the_geometric_mean(self):
        page = self.page([benchmark_row(cpython=2.0, pypy=0.5)])
        self.assertIn('<span class="time">2 s</span><span class="ratio same">reference</span>', page)
        self.assertIn('<span class="time">0.5 s</span><span class="ratio faster">4.0× faster</span>', page)
        self.assertIn("×4", page)
        self.assertIn("5 timed rounds", page)

    def test_slower_results(self):
        page = self.page([benchmark_row(cpython=1.0, pypy=2.5)])
        self.assertIn('<span class="ratio slower">2.5× slower</span>', page)
        self.assertIn('<span class="time">2.5 s</span>', page)

    def test_failed_benchmarks_show_their_status(self):
        page = self.page([benchmark_row(cpython=1.0, pypy={"status": "different", "detail": "Expected: 1"})])
        self.assertIn('<span class="status different">Different</span>', page)

    def test_a_report_without_benchmarks_says_so(self):
        self.assertIn(COPY["performanceEmpty"], self.page([]))

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
        self.assertIn(COPY["historyFirst"], pages["en"])
        self.assertIn("<circle", pages["en"])
        self.assertNotIn("<polyline", pages["en"])

    def test_several_runs_draw_lines_and_a_table_view(self):
        pages, _ = render(report(), self.previous("2026-11-11T05:00:00+00:00", "2026-11-18T05:00:00+00:00"))
        self.assertNotIn(COPY["historyFirst"], pages["en"])
        self.assertIn("<polyline", pages["en"])
        for day in ("2026-11-11", "2026-11-18", "2026-11-25"):
            self.assertIn(f"<th scope=\"row\">{day}</th>", pages["en"])
        self.assertIn(COPY["historyTable"], pages["en"])

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
    def describe(self, status, detail):
        return describe_observation({"status": status, "detail": detail}, COPY)

    def test_phrases_values_and_exceptions(self):
        self.assertEqual(self.describe("passed", "int: 6"), "Returns 6 (int)")
        self.assertEqual(self.describe("passed", "exception: ValueError"), "Raises ValueError")
        self.assertEqual(self.describe("different", "unexpected exception: AttributeError"),
                         "Raises an unexpected AttributeError")
        self.assertEqual(self.describe("different", "NoneType: None"), "Returns None")

    def test_leaves_measurement_problems_unchanged(self):
        detail = "Expected by the corpus: int: 6\nObserved: int: 7"
        self.assertEqual(self.describe("unverified", detail), detail)
        self.assertEqual(self.describe("missing", "sqlite3 No module named '_sqlite3'"),
                         "sqlite3 No module named '_sqlite3'")


if __name__ == "__main__":
    unittest.main()
