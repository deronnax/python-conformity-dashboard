import unittest

import update_ranking


try:
    from pip._vendor import packaging  # noqa: F401
except ImportError:
    packaging = None


def wheel(version, uploaded="2026-10-01T00:00:00Z", **extra):
    return {"filename": f"demo-{version}-py3-none-any.whl", "upload-time": uploaded, **extra}


@unittest.skipIf(packaging is None, "pip's vendored packaging is not importable")
class ChooseVersionTests(unittest.TestCase):
    CUTOFF = "2026-11-25"

    def choose(self, files, python="3.11"):
        return update_ranking.choose_version(files, self.CUTOFF, python)

    def test_picks_the_newest_stable_release(self):
        files = [wheel("1.9.0"), wheel("1.10.0"), wheel("2.0.0rc1"), wheel("2.0.0.dev3")]
        self.assertEqual(self.choose(files), "1.10.0")

    def test_skips_yanked_releases_and_later_uploads(self):
        files = [wheel("1.0"), wheel("1.1", yanked=True), wheel("1.2", yanked="broken"),
                 wheel("1.3", uploaded="2026-11-25T00:00:01Z")]
        self.assertEqual(self.choose(files), "1.0")

    def test_skips_releases_that_reject_this_python(self):
        files = [wheel("1.0", **{"requires-python": ">=3.8"}),
                 wheel("2.0", **{"requires-python": ">=3.12"}),
                 wheel("1.5", **{"requires-python": "!=3.0.*,!=3.11.*,>=2.7"})]
        self.assertEqual(self.choose(files), "1.0")

    def test_ignores_source_distributions(self):
        self.assertIsNone(self.choose([{"filename": "demo-1.0.tar.gz", "upload-time": "2026-10-01T00:00:00Z"}]))


class ChooseModuleTests(unittest.TestCase):
    def test_prefers_the_name_matching_the_project(self):
        self.assertEqual(update_ranking.choose_module("cffi", ["_cffi_backend", "cffi"]), "cffi")
        self.assertEqual(update_ranking.choose_module("typing-extensions", ["typing_extensions"]), "typing_extensions")

    def test_falls_back_to_the_first_public_name(self):
        self.assertEqual(update_ranking.choose_module("pyyaml", ["_yaml", "yaml"]), "yaml")
        self.assertEqual(update_ranking.choose_module("pyjwt", ["jwt"]), "jwt")

    def test_uses_overrides_for_namespaces_and_lazy_extensions(self):
        self.assertEqual(update_ranking.choose_module("protobuf", ["google"]), "google.protobuf")
        self.assertEqual(update_ranking.choose_module("pillow", ["PIL"]), "PIL.Image")


if __name__ == "__main__":
    unittest.main()
