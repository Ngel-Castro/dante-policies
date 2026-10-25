"""Collect, per molecule scenario, whether it passed and which characteristic
ids it declares.

A scenario declares ids in `molecule/<scenario>/characteristics.yml`:

    proves:
      - run-is-idempotent

Only tagged scenarios are run. An untagged one is listed with no ids (and is
reported as passed because nothing was run), so it neither covers anything nor
hides. Scenario output goes to stdout/stderr of the runner, never into the result.

Usage: python -m tools.collect_scenarios <repo> [--runner 'molecule test -s {scenario}']
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

DEFAULT_RUNNER = "molecule test -s {scenario}"


def declared_ids(scenario_dir: Path) -> list[str]:
    tag_file = scenario_dir / "characteristics.yml"
    if not tag_file.exists():
        return []
    data = yaml.safe_load(tag_file.read_text())
    proves = data.get("proves") if isinstance(data, dict) else None
    if not isinstance(proves, list) or not all(isinstance(i, str) for i in proves):
        raise ValueError(f"{scenario_dir.name}: characteristics.yml must hold `proves:` as a list of ids")
    return proves


def collect(repo: Path, runner: str = DEFAULT_RUNNER) -> list[dict]:
    repo = Path(repo)
    results = []
    for scenario_dir in sorted(p for p in (repo / "molecule").iterdir() if (p / "molecule.yml").exists()):
        ids = declared_ids(scenario_dir)
        passed = True
        if ids:
            cmd = shlex.split(runner.format(scenario=scenario_dir.name))
            passed = subprocess.run(cmd, cwd=repo, stdin=subprocess.DEVNULL, stdout=sys.stderr, stderr=sys.stderr).returncode == 0
        results.append({"name": scenario_dir.name, "passed": passed, "characteristics": ids})
    return results


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("--runner", default=DEFAULT_RUNNER)
    args = ap.parse_args(argv)
    print(json.dumps(collect(args.repo, args.runner), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
