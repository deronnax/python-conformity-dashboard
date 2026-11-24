"""Run one selected CPython test using the target interpreter's stdlib."""

import contextlib
import io
import json
import sys
import traceback
import unittest


def run_test(test_id):
    loader = unittest.TestLoader()
    try:
        suite = loader.loadTestsFromName(test_id)
    except unittest.SkipTest as exc:
        return "skipped", str(exc)
    except Exception:
        return "blocked", traceback.format_exc()
    if loader.errors or suite.countTestCases() != 1:
        return "blocked", "\n".join(loader.errors) or "Un seul test était attendu."

    outcome = unittest.TestResult()
    suite.run(outcome)
    if outcome.errors:
        return "error", outcome.errors[0][1]
    if outcome.failures:
        return "different", outcome.failures[0][1]
    if outcome.skipped or outcome.expectedFailures:
        return "skipped", str((outcome.skipped or outcome.expectedFailures)[0][1])
    if outcome.unexpectedSuccesses or outcome.testsRun != 1:
        return "blocked", "Le harnais n’a pas confirmé l’exécution du test."
    return "passed", ""


if __name__ == "__main__":
    sys.path.insert(0, sys.argv[1])
    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        status, detail = run_test(sys.argv[2])
    print(json.dumps({"status": status, "detail": detail or log.getvalue()}))
