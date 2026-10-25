"""Compare a policy with what a run produced.

characteristics: the ids tagged on scenarios that PASSED must cover every required
                 id in the policy; an id a scenario names that the policy does
                 not know is an error (a typo must not look like coverage).
static:          checkov's failed checks, filtered to the checks the policy
                 enables; a failure at a `fail_on` severity blocks.

Results carry ids, files and line ranges only. Never code, never values.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


def load_policy(path: Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text())


def characteristics_result(policy: dict, scenarios: list[dict]) -> dict:
    known = {c["id"] for c in policy["characteristics"]}
    required = [c["id"] for c in policy["characteristics"] if c.get("required", True)]
    covered: set[str] = set()
    tagged: set[str] = set()
    for s in scenarios:
        tagged.update(s["characteristics"])
        if s["passed"]:
            covered.update(s["characteristics"])
    unknown = sorted(tagged - known)
    missing = [i for i in required if i not in covered]
    return {
        "ok": not missing and not unknown,
        "required": required,
        "covered": sorted(covered & known),
        "missing": missing,
        "unknown": unknown,
    }


def static_result(policy: dict, checkov_json: dict) -> dict:
    sc = policy["static_checks"]
    severity = {c["id"]: c["severity"] for c in sc["checks"]}
    blocking: list[dict] = []
    advisory: list[dict] = []
    for f in checkov_json.get("results", {}).get("failed_checks", []):
        cid = f["check_id"]
        if cid not in severity:
            continue
        item = {
            "check_id": cid,
            "severity": severity[cid],
            "file": f.get("file_path"),
            "lines": f.get("file_line_range"),
        }
        (blocking if severity[cid] in sc["fail_on"] else advisory).append(item)
    return {"ok": not blocking, "blocking": blocking, "advisory": advisory}


def _read_scenarios(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text())


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--policy", required=True, type=Path)
    ap.add_argument("--policy-ref", help="the tag or commit the policy was pinned to")
    ap.add_argument("--policy-sha", help="the commit SHA the ref resolved to")
    ap.add_argument("--scenarios", type=Path, help="JSON list: name, passed, characteristics")
    ap.add_argument("--checkov-json", type=Path)
    args = ap.parse_args(argv)

    policy = load_policy(args.policy)
    out: dict[str, Any] = {
        "application_type": policy["application_type"],
        "policy_ref": args.policy_ref,
        "policy_sha": args.policy_sha,
    }
    ok = True
    if args.scenarios:
        out["characteristics"] = characteristics_result(policy, _read_scenarios(args.scenarios))
        ok &= out["characteristics"]["ok"]
    if args.checkov_json:
        raw = json.loads(args.checkov_json.read_text())
        raw = raw[0] if isinstance(raw, list) else raw
        out["static"] = static_result(policy, raw)
        ok &= out["static"]["ok"]
    out["ok"] = bool(ok)
    print(json.dumps(out, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
