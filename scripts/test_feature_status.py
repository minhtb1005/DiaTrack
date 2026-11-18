import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from feature_status import validate, verify, git, pilot_evidence

ledger = json.loads(Path("feature_list.json").read_text(encoding="utf8"))
sha = git("rev-parse", "HEAD")


class Gate(unittest.TestCase):
    def test_baseline(self):
        validate(ledger, ledger, sha)

    def test_blocked_handoff(self):
        changed = copy.deepcopy(ledger)
        changed["features"][8]["status"] = "done"
        with self.assertRaisesRegex(ValueError, "T09-AC04"):
            validate(ledger, changed, sha)

    def test_contract(self):
        changed = copy.deepcopy(ledger)
        changed["features"][8]["acceptance_criteria"][3]["description"] = "Always pass"
        with self.assertRaisesRegex(ValueError, "product review"):
            validate(ledger, changed, sha)

    def test_wip(self):
        changed = copy.deepcopy(ledger)
        for f in changed["features"][:2]:
            f["status"] = "in_progress"
        with self.assertRaisesRegex(ValueError, "WIP"):
            validate(ledger, changed, sha)

    def test_skipped_stale_and_missing_qa(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "result.xml")
            case = '<testcase classname="tests.test_api_diabetes.TestDiabetesAPI" name="test_glucose_110_roundtrip_and_ownership">{}</testcase>'
            report = {"snapshot": sha, "junit": path}
            review = {"snapshot": sha, "approved": ["T01-AC02"]}
            path.write_text(case.format("<skipped/>"))
            with self.assertRaisesRegex(ValueError, "unsuccessful"):
                verify("T01-AC02", sha, report, review)
            path.write_text(case.format(""))
            with self.assertRaisesRegex(ValueError, "stale"):
                verify("T01-AC02", "other", report, review)
            with self.assertRaisesRegex(ValueError, "independent QA"):
                verify("T01-AC02", sha, report, None)
            verify("T01-AC02", sha, report, review)


if __name__ == "__main__":
    if "--pilot-report" in sys.argv:
        # CI generates this report in the immediately preceding step.
        verify("T01-AC02", sha, *pilot_evidence(sha, Path(sys.argv[-1])))
        print("T01-AC02 passed with independently reviewed inputs")
    else:
        unittest.main()
