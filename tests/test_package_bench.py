import unittest
from pathlib import Path
from unittest import mock

import package_bench


PYPY_8 = {"interpreter": "pp312", "abi": "pypy312_pp80", "platform": "manylinux_2_39_x86_64"}
PACKAGE = {"project": "lxml", "version": "6.1.3", "module": "lxml.etree"}


class ForeignAbiTests(unittest.TestCase):
    def test_reports_wheels_for_another_abi_of_the_same_interpreter(self):
        filenames = [
            "lxml-6.1.3-pp312-pypy312_pp73-manylinux2014_x86_64.manylinux_2_17_x86_64.whl",
            "lxml-6.1.3-pp312-pypy312_pp73-manylinux_2_28_aarch64.whl",
            "lxml-6.1.3-pp310-pypy310_pp73-manylinux_2_28_x86_64.whl",
            "lxml-6.1.3-pp312-pypy312_pp73-macosx_11_0_x86_64.whl",
            "lxml-6.1.3-cp312-cp312-manylinux_2_28_x86_64.whl",
            "lxml-6.1.3.tar.gz",
        ]
        self.assertEqual(package_bench.foreign_abis(filenames, PYPY_8), ["pypy312_pp73"])

    def test_ignores_the_abi_the_interpreter_requires(self):
        filenames = ["pyzmq-27.3.0-pp312-pypy312_pp80-manylinux_2_28_x86_64.whl"]
        self.assertEqual(package_bench.foreign_abis(filenames, PYPY_8), [])

    def test_reads_legacy_manylinux_tags(self):
        self.assertEqual(package_bench.platform_family("manylinux1_x86_64"), ("linux", "x86_64"))
        self.assertEqual(package_bench.platform_family("musllinux_1_2_x86_64"), ("linux", "x86_64"))
        self.assertEqual(package_bench.platform_family("macosx_11_0_universal2"), ("macosx", "universal2"))


# The wheels cryptography 50.0.2 publishes for x86-64 Linux and for PyPy.
CRYPTOGRAPHY = [
    "cryptography-50.0.2-cp311-abi3-manylinux_2_28_x86_64.whl",
    "cryptography-50.0.2-cp314-cp314t-manylinux_2_28_x86_64.whl",
    "cryptography-50.0.2-pp311-pypy311_pp73-manylinux_2_28_x86_64.whl",
    "cryptography-50.0.2-pp311-pypy311_pp73-manylinux_2_34_aarch64.whl",
    "cryptography-50.0.2-pp311-pypy311_pp80-macosx_11_0_arm64.whl",
    "cryptography-50.0.2-pp311-pypy311_pp80-win_amd64.whl",
    "cryptography-50.0.2.tar.gz",
]
GRAALPY = {"interpreter": "graalpy312", "abi": "graalpy250_312_native", "platform": "manylinux_2_39_x86_64"}


class OtherPythonVersionTests(unittest.TestCase):
    def test_reports_wheels_of_the_same_implementation_for_another_python(self):
        self.assertEqual(package_bench.other_python_versions(CRYPTOGRAPHY, PYPY_8), ["pp311"])

    def test_ignores_other_platforms_and_implementations(self):
        self.assertEqual(package_bench.other_python_versions(CRYPTOGRAPHY, GRAALPY), [])
        macos = {**PYPY_8, "platform": "macosx_14_0_x86_64"}
        self.assertEqual(package_bench.other_python_versions(CRYPTOGRAPHY, macos), [])

    def test_version_independent_wheels_do_not_count(self):
        freethreaded = {"interpreter": "cp313", "abi": "cp313t", "platform": "manylinux_2_39_x86_64"}
        self.assertEqual(package_bench.other_python_versions(CRYPTOGRAPHY, freethreaded), ["cp314"])
        self.assertEqual(package_bench.other_python_versions(CRYPTOGRAPHY[:1], freethreaded), [])


class MissingWheelTests(unittest.TestCase):
    def test_classifies_a_release_built_for_another_abi(self):
        files = ["lxml-6.1.3-pp312-pypy312_pp73-manylinux_2_28_x86_64.whl"]
        with mock.patch.object(package_bench, "release_files", return_value=files):
            outcome = package_bench.missing_wheel(
                PACKAGE, "ERROR: No matching distribution found for lxml==6.1.3", PYPY_8, Path("/tmp/bench"))
        self.assertEqual(outcome["status"], "otherAbi")
        self.assertIn("pypy312_pp73", outcome["detail"])
        self.assertIn("pypy312_pp80", outcome["detailFr"])

    def test_classifies_a_release_built_for_another_python_version(self):
        package = {"project": "cryptography", "version": "50.0.2", "module": "cryptography"}
        with mock.patch.object(package_bench, "release_files", return_value=CRYPTOGRAPHY):
            outcome = package_bench.missing_wheel(
                package, "ERROR: No matching distribution found for cryptography==50.0.2", PYPY_8, Path("/tmp/bench"))
        self.assertEqual(outcome["status"], "otherPython")
        self.assertIn("pp311", outcome["detail"])
        self.assertIn("pp312", outcome["detailFr"])

    def test_another_abi_takes_precedence_over_another_python(self):
        files = CRYPTOGRAPHY + ["lxml-6.1.3-pp312-pypy312_pp73-manylinux_2_28_x86_64.whl"]
        with mock.patch.object(package_bench, "release_files", return_value=files):
            outcome = package_bench.missing_wheel(
                PACKAGE, "ERROR: No matching distribution found for lxml==6.1.3", PYPY_8, Path("/tmp/bench"))
        self.assertEqual(outcome["status"], "otherAbi")

    def test_keeps_missing_dependencies_as_missing_wheels(self):
        with mock.patch.object(package_bench, "release_files") as lookup:
            outcome = package_bench.missing_wheel(
                PACKAGE, "ERROR: No matching distribution found for cffi>=1.0", PYPY_8, Path("/tmp/bench"))
        lookup.assert_not_called()
        self.assertEqual(outcome["status"], "noWheel")

    def test_keeps_the_pip_message_when_pypi_is_unreachable(self):
        with mock.patch.object(package_bench, "release_files", side_effect=OSError("offline")):
            outcome = package_bench.missing_wheel(
                PACKAGE, "ERROR: No matching distribution found for lxml==6.1.3", PYPY_8, Path("/tmp/bench"))
        self.assertEqual(outcome, {"status": "noWheel", "detail": "ERROR: No matching distribution found for lxml==6.1.3"})


if __name__ == "__main__":
    unittest.main()
