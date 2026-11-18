"""Read-only PR check. The caller supplies reports and review decisions from CI."""
import argparse
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

BASELINE = "ac8c88d19b34de4fdc6e097d4e015ea98c602762"
OWNERSHIP = ("tests.test_api_diabetes.TestDiabetesAPI", "test_glucose_110_roundtrip_and_ownership")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def indexed(rows):
    result = {}
    for row in rows:
        key = row["id"]
        require(isinstance(key, str) and key and key not in result, f"Invalid or duplicate ID: {key}")
        result[key] = row
    return result


def verify(ac, snapshot, report, review):
    require(ac == "T01-AC02", f"{ac}: no approved evidence mapping")
    require(report and report["snapshot"] == snapshot, f"{ac}: missing or stale report")
    root = ET.parse(report["junit"]).getroot()
    cases = [c for c in root.iter("testcase") if (c.get("classname"), c.get("name")) == OWNERSHIP]
    require(len(cases) == 1 and not any(cases[0].find(tag) is not None for tag in ("failure", "error", "skipped")), f"{ac}: ownership test absent or unsuccessful")
    require(review and review["snapshot"] == snapshot and ac in review["approved"], f"{ac}: independent QA missing")


def validate(base, current, snapshot, report=None, review=None, product_approved=False, affected=()):
    old, new = indexed(base["features"]), indexed(current["features"])
    require(not (old.keys() - new.keys()) or product_approved, "Feature removed without product review")
    require(sum(f["status"] == "in_progress" for f in new.values()) <= 1, "WIP exceeds one")
    seen = set()
    for key, f in new.items():
        status, deps = f["status"], f["dependencies"]
        require(status in {"todo","partial","done","blocked","in_progress"}, f"{key}: unknown status")
        require(key not in deps and all(d in new for d in deps), f"{key}: invalid dependency")
        stack, visited = list(deps), set()
        while stack:
            dep = stack.pop()
            require(dep != key and dep in new, f"{key}: invalid dependency graph")
            if dep not in visited:
                visited.add(dep)
                stack.extend(new[dep]["dependencies"])
        if status == "in_progress" or (status == "done" and old.get(key, {}).get("status") != "done"):
            require(all(new[d]["status"] == "done" for d in deps), f"{key}: unfinished dependency")
        ac, uc = indexed(f["acceptance_criteria"]), indexed(f["use_cases"])
        require(ac and uc and not seen.intersection(set(ac)|set(uc)) and ac.keys().isdisjoint(uc), f"{key}: invalid IDs")
        seen.update(ac); seen.update(uc)
        require(all(u["acceptance_criterion"] in ac for u in uc.values()), f"{key}: dangling criterion")
        prior = old.get(key, {})
        contract_changed = prior and any(prior[k] != f[k] for k in ("use_cases","acceptance_criteria","dependencies"))
        require(not contract_changed or product_approved, f"{key}: contract needs product review")
        if status == "blocked":
            require(isinstance(f.get("blocked_reason"), str) and f["blocked_reason"].strip(), f"{key}: missing blocker")
        if f == prior and key not in affected:
            continue
        if status == "partial":
            ref = f.get("implementation_ref", "")
            require(ref in git("ls-files").splitlines() and f.get("remaining_criteria") and set(f["remaining_criteria"]) <= ac.keys(), f"{key}: cite implementation and remaining criteria")
        if status == "done":
            errors = []
            for aid in ac:
                try:
                    verify(aid, snapshot, report, review)
                except ValueError as error:
                    errors.append(str(error))
            require(not errors, " | ".join(errors))


def git(*args):
    return subprocess.check_output(["git", *args], text=True, encoding="utf8").strip()


def pilot_evidence(snapshot, junit):
    require(Path(str(junit) + ".sha").read_text().strip() == snapshot, "Stale pilot snapshot")
    review = json.loads(Path("docs/feature-pilot-qa.json").read_text())
    expected = {"src", "tests/conftest.py", "tests/test_api_diabetes.py", "tests/__init__.py", "pyproject.toml", "scripts/run_feature_pilot.py"}
    if set(review["reviewed_files"]) != expected:
        raise SystemExit("QA scope incomplete")
    for path, blob in review["reviewed_files"].items():
        if git("rev-parse","HEAD:"+path) != blob:
            raise SystemExit("QA snapshot changed: " + path)
    return {"snapshot": snapshot, "junit": junit}, {"snapshot": snapshot, "approved": review["approved"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--pilot-report", type=Path)
    parser.add_argument("--affected", action="append", default=[])
    args = parser.parse_args()
    base_ref = args.base
    if not git("ls-tree", base_ref, "feature_list.json"):
        require(git("merge-base", BASELINE, "HEAD") == BASELINE, "Missing migration baseline")
        base_ref = BASELINE
    changed = git("diff","--name-only",args.base,"HEAD").splitlines()
    product = any(p.startswith(("src/","frontend/","tests/","data/")) for p in changed)
    current = json.loads(Path("feature_list.json").read_text(encoding="utf8"))
    affected = set(args.affected) | set(current.get("affected_features", []))
    require(not product or affected, "Declare affected_features for product/test changes")
    require(affected <= indexed(current["features"]).keys(), "Unknown affected feature")
    approvers = set(os.environ.get("PRODUCT_REVIEWERS", "").split())
    decisions = {}
    for review in json.loads(os.environ.get("PR_REVIEWS", "[]")):
        if review["state"] != "COMMENTED":
            decisions[review["user"]["login"]] = review
    approved = any(name in approvers and name != os.environ.get("PR_AUTHOR") and r["state"] == "APPROVED" and r["commit_id"] == git("rev-parse", "HEAD") for name, r in decisions.items())
    snapshot = git("rev-parse", "HEAD")
    report, qa = pilot_evidence(snapshot, args.pilot_report) if args.pilot_report else (None, None)
    validate(json.loads(git("show", base_ref + ":feature_list.json")), current, snapshot, report, qa, approved, affected)
    print("Feature status check passed")
