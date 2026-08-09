#!/usr/bin/env python3
"""Run the full acceptance suite with an explicit tally.

    python3 tools/run_tests.py            # everything
    python3 tools/run_tests.py -q         # quiet (dots only + tally)

Exit code 0 only if nothing failed or errored.
"""
import sys, os, unittest

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    verbosity = 1 if "-q" in sys.argv else 2
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=os.path.join(HERE, "tests"))
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    total   = result.testsRun
    failed  = len(result.failures)
    errors  = len(result.errors)
    skipped = len(result.skipped)
    passed  = total - failed - errors - skipped
    print("=" * 60)
    print("TESTS: total=%d  passed=%d  failed=%d  errors=%d  skipped=%d"
          % (total, passed, failed, errors, skipped))
    for test, reason in result.skipped:
        print("  skipped: %s — %s" % (test.id().split('.')[-2], reason))
    print("RESULT: %s" % ("PASS ✓" if result.wasSuccessful() else "FAIL ✗"))
    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == "__main__":
    main()
