# dante-policies

Policies the Dante pipelines check applications against, kept in git so a change
is a reviewed pull request and a result can name the exact version it used.

**This repository is public.** A pipeline clones it anonymously over https and pins a tag
or a commit; no key or token is needed to read it.

One folder per application type. Today: `ansible-vm/`.

```
<application-type>/
  policy.yaml     required key characteristics + the static checks that are enabled
  checks/         custom checkov checks (Python or YAML), one id each
schema/policy.schema.json   what a policy file may contain
tools/                      lint, compare, pin
tests/
```

## A policy file

* `characteristics`: short ids with a one-line meaning. A test scenario (a molecule
  scenario, later a Playwright feature) declares the ids it proves. A required id that no
  *passing* scenario proves fails the check.
* `static_checks`: the checkov checks that are enabled, each with a severity, and
  `fail_on`: the severities that block. A failure below `fail_on` is reported, not blocking.

## Tools

```bash
pip install -r requirements.txt
python -m tools.lint_policy                       # every */policy.yaml; CI runs this
python -m pytest -q

# in the application's repository: run the tagged scenarios, list ids from the passing ones
python -m tools.collect_scenarios <app-repo> > scenarios.json
checkov -d <app-repo> --framework ansible --external-checks-dir ansible-vm/checks -o json > checkov.json

# compare (exit 1 when not compliant); print the policy version used
SHA=$(python -m tools.resolve_pin <this-repo-url-or-path> <tag-or-commit>)
python -m tools.evaluate --policy ansible-vm/policy.yaml --policy-ref <tag> --policy-sha "$SHA" \
  --scenarios scenarios.json --checkov-json checkov.json
```

A pin is a tag or a commit. `resolve_pin` refuses a branch, and prints the commit a tag
points at, so an old result stays explainable after the tag moves.

## Declaring what a scenario proves (molecule)

`molecule/<scenario>/characteristics.yml` in the application repository:

```yaml
---
proves:
  - run-is-idempotent
```

Only tagged scenarios are run by `collect_scenarios`.

## Custom checks

* **Python** when the check needs to look at what a task contains (`NoLogOnSecretTasks.py`).
  The directory needs an `__init__.py`, or checkov loads nothing and says nothing.
* **YAML** when it is "this attribute must exist or equal X" on one module
  (`get-url-timeout.yaml`). Task-level keys such as `no_log` are visible too.

Every `CKV_DANTE_*` id in the code must be enabled in the policy and the other way round;
the lint enforces both.

## What never goes here

Everything here is world-readable. No credential of any kind, no internal hostname or
address, no account id: a policy is generic or names environments only. Results carry ids,
files and line ranges only, never code or values.
