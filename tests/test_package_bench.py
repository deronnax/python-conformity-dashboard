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
        self.assertIn("pypy312_pp80", outcome["detail"])

    def test_classifies_a_release_built_for_another_python_version(self):
        package = {"project": "cryptography", "version": "50.0.2", "module": "cryptography"}
        with mock.patch.object(package_bench, "release_files", return_value=CRYPTOGRAPHY):
            outcome = package_bench.missing_wheel(
                package, "ERROR: No matching distribution found for cryptography==50.0.2", PYPY_8, Path("/tmp/bench"))
        self.assertEqual(outcome["status"], "otherPython")
        self.assertIn("pp311", outcome["detail"])
        self.assertIn("pp312", outcome["detail"])

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


class SourceFallbackTests(unittest.TestCase):
    def test_only_the_projects_own_missing_wheel_triggers_the_fallback(self):
        line = "ERROR: No matching distribution found for markupsafe==3.0.4"
        self.assertTrue(package_bench.sdist_fallback({"project": "MarkupSafe"}, line))
        self.assertFalse(package_bench.sdist_fallback({"project": "jinja2"}, line))

    def test_only_the_tested_project_may_build_from_source(self):
        arguments = package_bench.install_arguments(Path("/tmp/prefix"), "pypy", "markupsafe")
        self.assertEqual(arguments[arguments.index("--no-binary") + 1], "markupsafe")
        self.assertIn("--only-binary=:all:", arguments)
        self.assertNotIn("--no-binary", package_bench.install_arguments(Path("/tmp/prefix"), "pypy"))


RESOLUTION = """\
ERROR: Cannot install jsonschema-specifications==2025.9.1 because these package versions have conflicting dependencies.

The conflict is caused by:
    jsonschema-specifications 2025.9.1 depends on referencing>=0.31.0
    referencing 0.37.0 depends on rpds-py>=0.7.0; python_version >= "3.9"

To fix this you could try to:
1. loosen the range of package versions you've specified

ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/topics/dependency-resolution/
"""
RPDS = {"2026.9.1": ["rpds_py-2026.9.1-pp312-pypy312_pp73-manylinux_2_28_x86_64.whl"],
        "0.1.0": ["rpds_py-0.1.0.tar.gz"]}


class BlockingDependencyTests(unittest.TestCase):
    def test_reads_the_dependency_pip_found_no_wheel_for(self):
        output = "ERROR: Could not find a version\nERROR: No matching distribution found for rpds-py>=0.25.0\n"
        self.assertEqual(package_bench.blocking_requirements(output, "jsonschema"), [("rpds-py", ">=0.25.0")])

    def test_the_package_itself_is_not_a_dependency(self):
        output = "ERROR: No matching distribution found for cryptography==50.0.2"
        self.assertEqual(package_bench.blocking_requirements(output, "cryptography"), [])

    def test_reads_the_dependencies_of_a_resolution_conflict(self):
        self.assertEqual(package_bench.blocking_requirements(RESOLUTION, "jsonschema-specifications"),
                         [("referencing", ">=0.31.0"), ("rpds-py", ">=0.7.0")])

    def test_explains_why_the_dependency_has_no_usable_wheel(self):
        with mock.patch.object(package_bench, "project_releases", return_value=RPDS):
            blocker = package_bench.describe_dependency("rpds-py", ">=0.25.0", PYPY_8)
        self.assertEqual(blocker, {"name": "rpds-py", "requirement": "rpds-py>=0.25.0", "version": "2026.9.1",
                                   "cause": "otherAbi", "published": ["pypy312_pp73"]})

    def test_an_unreachable_index_keeps_the_requirement_only(self):
        with mock.patch.object(package_bench, "project_releases", side_effect=OSError("offline")):
            blocker = package_bench.describe_dependency("rpds-py", ">=0.25.0", PYPY_8)
        self.assertEqual(blocker, {"name": "rpds-py", "requirement": "rpds-py>=0.25.0"})

    def test_a_blocked_installation_names_its_dependency(self):
        output = "ERROR: No matching distribution found for rpds-py>=0.25.0"
        with mock.patch.object(package_bench, "project_releases", return_value=RPDS):
            outcome = package_bench.blocked_by({"project": "jsonschema"}, output, PYPY_8, Path("/tmp/bench"))
        self.assertEqual(outcome["status"], "dependency")
        self.assertEqual(outcome["blocker"]["name"], "rpds-py")
        self.assertIsNone(package_bench.blocked_by({"project": "rpds-py"}, output.replace(">=0.25.0", "==2026.9.1"),
                                                   PYPY_8, Path("/tmp/bench")))


class PurePythonTests(unittest.TestCase):
    def test_detects_a_pure_python_wheel(self):
        files = ["requests-2.34.2-py3-none-any.whl", "requests-2.34.2.tar.gz"]
        with mock.patch.object(package_bench, "release_files", return_value=files):
            self.assertTrue(package_bench.pure_python({"project": "requests", "version": "2.34.2"}))
        with mock.patch.object(package_bench, "release_files", return_value=CRYPTOGRAPHY):
            self.assertFalse(package_bench.pure_python({"project": "cryptography", "version": "50.0.2"}))

    def test_native_packages_are_not_tested(self):
        self.assertEqual(package_bench.native_only({"purePython": False})["status"], "nativeOnly")
        self.assertEqual(package_bench.native_only({"purePython": None})["status"], "blocked")


class FunctionalCheckTests(unittest.TestCase):
    """Run the import script on a fake installed distribution."""

    def run_check(self, check):
        import json
        import subprocess
        import sys
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as site:
            Path(site, "demo").mkdir()
            Path(site, "demo", "__init__.py").write_text("VALUE = 2\n", encoding="utf-8")
            Path(site, "demo-1.0.dist-info").mkdir()
            Path(site, "demo-1.0.dist-info", "METADATA").write_text(
                "Metadata-Version: 2.1\nName: demo\nVersion: 1.0\n", encoding="utf-8")
            completed = subprocess.run([sys.executable, "-I", "-c", package_bench.IMPORT_PACKAGE, site, "demo", "1.0",
                                        "demo", check], capture_output=True, text=True, timeout=60)
        return json.loads(completed.stdout.splitlines()[-1])

    def test_a_package_without_a_check_is_import_only(self):
        self.assertEqual(self.run_check(""), {"status": "passed", "detail": "", "level": "import"})

    def test_a_passing_check_makes_the_package_functional(self):
        self.assertEqual(self.run_check("import demo\nassert demo.VALUE == 2")["level"], "functional")

    def test_a_failing_check_is_a_functional_error(self):
        outcome = self.run_check("import demo\nassert demo.VALUE == 3, 'wrong value'")
        self.assertEqual(outcome["status"], "functionError")
        self.assertIn("AssertionError: wrong value", outcome["detail"])

    def test_every_check_names_a_ranked_project(self):
        import json
        from smoke import SMOKE
        from references import REFERENCES
        for reference in REFERENCES.values():
            projects = {item["project"] for item in json.loads(reference.ranking.read_text(encoding="utf-8"))["items"]}
            self.assertEqual(set(SMOKE) - projects, set())


if __name__ == "__main__":
    unittest.main()
