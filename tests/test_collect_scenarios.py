import json

import pytest
import yaml

from tools.collect_scenarios import collect


def make(tmp_path, **scenarios):
    for name, ids in scenarios.items():
        d = tmp_path / "molecule" / name
        d.mkdir(parents=True)
        (d / "molecule.yml").write_text("{}")
        if ids is not None:
            (d / "characteristics.yml").write_text(yaml.safe_dump({"proves": ids}))
    return tmp_path


def test_a_tagged_passing_scenario_is_reported_with_its_ids(tmp_path):
    repo = make(tmp_path, default=["run-is-idempotent"])
    out = collect(repo, "true {scenario}")
    assert out == [{"name": "default", "passed": True, "characteristics": ["run-is-idempotent"]}]


def test_a_failing_scenario_is_reported_as_not_passed(tmp_path):
    repo = make(tmp_path, default=["run-is-idempotent"])
    assert collect(repo, "false {scenario}")[0]["passed"] is False


def test_an_untagged_scenario_is_listed_with_no_ids_and_is_not_run(tmp_path):
    repo = make(tmp_path, relay=None)
    out = collect(repo, "false {scenario}")
    assert out == [{"name": "relay", "passed": True, "characteristics": []}]


def test_the_runner_gets_the_scenario_name(tmp_path):
    repo = make(tmp_path, ipv6=["setting-survives-reboot"])
    marker = tmp_path / "ran"
    collect(repo, f"sh -c 'echo {{scenario}} > {marker}'")
    assert marker.read_text().strip() == "ipv6"


def test_a_malformed_tag_file_is_an_error(tmp_path):
    repo = make(tmp_path, default=["ok"])
    (repo / "molecule" / "default" / "characteristics.yml").write_text("proves: not-a-list")
    with pytest.raises(ValueError, match="default"):
        collect(repo, "true {scenario}")


def test_output_is_json_serialisable(tmp_path):
    repo = make(tmp_path, default=["run-is-idempotent"])
    json.dumps(collect(repo, "true {scenario}"))
