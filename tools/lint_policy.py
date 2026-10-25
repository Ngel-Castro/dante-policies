"""Lint a policy file: schema, uniqueness, and agreement with the check code.

Usage: python -m tools.lint_policy [policy.yaml ...]   (default: every */policy.yaml)
Exit 1 when any error is found. Errors name ids and files, never values.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
CUSTOM_PREFIX = "CKV_DANTE_"
_ID_IN_PY = re.compile(r"""\bid\s*=\s*["'](CKV_DANTE_[A-Z0-9_]+)["']""")
_ID_IN_YAML = re.compile(r"""^\s*id:\s*["']?(CKV_DANTE_[A-Z0-9_]+)["']?\s*$""", re.M)


def custom_check_ids(checks_dir: Path) -> set[str]:
    found: set[str] = set()
    if not checks_dir.is_dir():
        return found
    for path in sorted(checks_dir.iterdir()):
        if path.suffix == ".py":
            found.update(_ID_IN_PY.findall(path.read_text()))
        elif path.suffix in (".yaml", ".yml"):
            found.update(_ID_IN_YAML.findall(path.read_text()))
    return found


def lint(policy_path: Path, root: Path = ROOT) -> list[str]:
    try:
        data = yaml.safe_load(Path(policy_path).read_text())
    except yaml.YAMLError as exc:
        return [f"{policy_path}: not valid YAML ({type(exc).__name__})"]

    schema = json.loads((root / "schema" / "policy.schema.json").read_text())
    errors = [
        f"{policy_path}: {'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
        for e in sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))
    ]
    if errors:
        return errors

    seen: set[str] = set()
    for c in data["characteristics"]:
        if c["id"] in seen:
            errors.append(f"{policy_path}: duplicate characteristic id {c['id']}")
        seen.add(c["id"])

    static = data["static_checks"]
    enabled: set[str] = set()
    for c in static["checks"]:
        if c["id"] in enabled:
            errors.append(f"{policy_path}: duplicate check id {c['id']}")
        enabled.add(c["id"])

    in_code = custom_check_ids(root / static["custom_checks_dir"]) if "custom_checks_dir" in static else set()
    for cid in sorted(i for i in enabled if i.startswith(CUSTOM_PREFIX) and i not in in_code):
        errors.append(f"{policy_path}: {cid} is enabled but there is no check with that id in the custom checks directory")
    for cid in sorted(in_code - enabled):
        errors.append(f"{policy_path}: {cid} exists as code but is not enabled in the policy")
    return errors


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv] or sorted(ROOT.glob("*/policy.yaml"))
    if not paths:
        print("no policy files found", file=sys.stderr)
        return 1
    errors = [e for p in paths for e in lint(p)]
    for e in errors:
        print(e, file=sys.stderr)
    print(f"{len(paths)} policy file(s), {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
