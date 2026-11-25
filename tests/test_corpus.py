import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import corpus
import measure


class ContractTests(unittest.TestCase):
    def test_every_case_has_a_known_contract(self):
        for probe in corpus.PROBES:
            with self.subTest(probe=probe.id):
                self.assertIn(probe.contract, corpus.CONTRACT_KINDS)

    def test_documented_cases_link_to_the_reference_documentation(self):
        for probe in corpus.PROBES:
            if probe.contract == "stdlib_spec":
                with self.subTest(probe=probe.id):
                    self.assertTrue(probe.contract_source.startswith("https://docs.python.org/3.12/library/"))
                    self.assertIn("#", probe.contract_source)

    def test_the_classification_names_only_existing_cases(self):
        self.assertEqual(set(corpus.CONTRACTS) - {probe.id for probe in corpus.PROBES}, set())

    def test_the_mmap_buffer_case_cites_no_upstream_test(self):
        # MmapTests.test_context_manager never creates a memoryview.
        probe = next(probe for probe in corpus.PROBES if probe.id == "mmap-memoryview")
        self.assertIsNone(probe.upstream)
        self.assertEqual(probe.contract, "cpython_behavior")
        self.assertIsNone(corpus.source_url(probe.upstream))



class SourceLinkTests(unittest.TestCase):
    def test_links_point_to_the_method_line_including_inherited_ones(self):
        with TemporaryDirectory() as lib:
            module = Path(lib, "test", "test_demo.py")
            module.parent.mkdir()
            module.write_text("class Base:\n    def test_one(self):\n        pass\n\n"
                              "class Child(Base):\n    pass\n", encoding="utf-8")
            url = corpus.source_url("test.test_demo.Child.test_one", lib)
            self.assertTrue(url.endswith("/Lib/test/test_demo.py#L2"))
            self.assertIn(f"/v{corpus.CPYTHON_VERSION}/", url)
            self.assertFalse(corpus.source_url("test.test_demo.Child.test_missing", lib).endswith("#L2"))

    def test_links_fall_back_to_the_file_without_sources(self):
        self.assertTrue(corpus.source_url("test.test_demo.Child.test_one").endswith("/Lib/test/test_demo.py"))

def completed(returncode, stderr="", stdout=""):
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


class FailureClassificationTests(unittest.TestCase):
    def invoke(self, process):
        with mock.patch.object(measure, "run", return_value=process):
            return measure.invoke("python", "-c", "pass", cwd=".")

    def test_a_host_exception_is_an_internal_interpreter_error(self):
        trace = "java.lang.ClassCastException: com.oracle.truffle.api.strings.TruffleString cannot be cast"
        self.assertEqual(self.invoke(completed(1, trace))["status"], "internalError")

    def test_a_signal_is_a_crash(self):
        self.assertEqual(self.invoke(completed(-11))["status"], "crash")

    def test_an_unexplained_exit_stays_blocked(self):
        outcome = self.invoke(completed(1, "Traceback (most recent call last):\nOSError: no space left"))
        self.assertEqual(outcome["status"], "blocked")

    def test_output_is_returned_on_success(self):
        self.assertEqual(self.invoke(completed(0, stdout="value int 6\n")), "value int 6")


class VersionTests(unittest.TestCase):
    def test_only_another_minor_version_is_a_cross_version_comparison(self):
        self.assertFalse(measure.language_mismatch("3.12.8", "3.12.15"))
        self.assertTrue(measure.language_mismatch("3.14.9", "3.12.15"))
        self.assertTrue(measure.language_mismatch("3.14.0a0", "3.12.15"))


if __name__ == "__main__":
    unittest.main()
