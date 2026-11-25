import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dashboard import describe_observation, generate
from dashboard_content import TRANSLATIONS


RUNTIMES = [
    {"id": "cpython", "name": "CPython", "version": "3.11.17 (main) [Clang]"},
    {"id": "pypy", "name": "PyPy", "version": "3.11.17 (abc)\n[PyPy 8.0.1 with GCC]"},
]


def passed(detail=""):
    return {"status": "passed", "detail": detail}


def report(**overrides):
    base = {
        "generatedAt": "2026-11-25T14:58:13+00:00",
        "platform": "Linux 7.0 · x86_64",
        "reference": "3.11.17",
        "runtimes": RUNTIMES,
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


def render(data):
    with TemporaryDirectory() as directory:
        output = Path(directory)
        generate(data, output)
        pages = {language: (output / path).read_text(encoding="utf-8")
                 for language, path in (("en", "index.html"), ("fr", "fr/index.html"))}
        saved = json.loads((output / "results.json").read_text(encoding="utf-8"))
    return pages, saved


class GenerateTests(unittest.TestCase):
    def test_renders_every_view_in_both_languages(self):
        pages, saved = render(report())
        self.assertEqual(saved["reference"], "3.11.17")
        for language, page in pages.items():
            for anchor in ("pypi-packages", "applications", "shared-cases", "cpython-tests"):
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
