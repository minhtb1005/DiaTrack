import copy
import json
import tempfile
import unittest
from pathlib import Path
from feature_status import validate, verify, git

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
                verify(ledger["features"][0]["acceptance_criteria"][1], sha, report, review)
            path.write_text(case.format(""))
            with self.assertRaisesRegex(ValueError, "stale"):
                verify(ledger["features"][0]["acceptance_criteria"][1], "other", report, review)
            with self.assertRaisesRegex(ValueError, "independent QA"):
                verify(ledger["features"][0]["acceptance_criteria"][1], sha, report, None)
            verify(ledger["features"][0]["acceptance_criteria"][1], sha, report, review)


    def test_done_requires_all_declared_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "junit.xml")
            report = {"snapshot": sha, "junit": path}
            f = {"id": "example", "status": "todo", "dependencies": [],
                 "acceptance_criteria": [{"id": "a", "tests": ["tests/test_demo.py::test_a", "tests/test_demo.py::test_b"], "requires_qa": False}],
                 "use_cases": [{"id": "u", "acceptance_criterion": "a"}]}
            base = {"features": [f]}
            changed = copy.deepcopy(base)
            changed["features"][0]["status"] = "done"
            case = '<testcase classname="tests.test_demo" name="test_{}"/>'
            path.write_text(case.format("a"))
            with self.assertRaisesRegex(ValueError, "test_b"):
                validate(base, changed, sha, report)
            path.write_text("<testsuite>" + case.format("a") + case.format("b") + "</testsuite>")
            validate(base, changed, sha, report)

    def test_removing_a_mapped_test_needs_review(self):
        changed = copy.deepcopy(ledger)
        changed["features"][0]["acceptance_criteria"][1]["tests"] = []
        with self.assertRaisesRegex(ValueError, "weakening verification"):
            validate(ledger, changed, sha)


if __name__ == "__main__":
    unittest.main()
