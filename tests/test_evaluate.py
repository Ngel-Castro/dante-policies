import pytest

from tools.evaluate import characteristics_result, load_policy, static_result


@pytest.fixture
def policy(repo):
    return load_policy(repo / "ansible-vm" / "policy.yaml")


ALL_BUT_HTTPS = [
    "linked-secrets-reach-playbook",
    "setting-survives-reboot",
    "run-is-idempotent",
    "no-secret-in-log",
]


def scenarios(**kw):
    return [{"name": n, "passed": v[0], "characteristics": v[1]} for n, v in kw.items()]


def test_all_required_ids_proved_by_passing_scenarios_passes(policy):
    ids = ALL_BUT_HTTPS + ["https-enabled"]
    result = characteristics_result(policy, scenarios(default=(True, ids)))
    assert result["ok"] is True
    assert result["missing"] == []


def test_a_required_id_with_no_scenario_fails_and_is_named(policy):
    result = characteristics_result(policy, scenarios(default=(True, ALL_BUT_HTTPS)))
    assert result["ok"] is False
    assert result["missing"] == ["https-enabled"]


def test_ids_of_a_failing_scenario_do_not_count(policy):
    ids = ALL_BUT_HTTPS + ["https-enabled"]
    result = characteristics_result(policy, scenarios(default=(True, ALL_BUT_HTTPS), other=(False, ["https-enabled"])))
    assert result["ok"] is False
    assert result["missing"] == ["https-enabled"]
    assert ids  # keep the full list referenced


def test_a_scenario_tagged_with_an_unknown_id_is_an_error_not_a_pass(policy):
    result = characteristics_result(policy, scenarios(default=(True, ALL_BUT_HTTPS + ["https-enabled", "https-enabeld"])))
    assert result["unknown"] == ["https-enabeld"]
    assert result["ok"] is False


def test_optional_characteristics_do_not_fail_when_missing(policy):
    for c in policy["characteristics"]:
        if c["id"] == "https-enabled":
            c["required"] = False
    result = characteristics_result(policy, scenarios(default=(True, ALL_BUT_HTTPS)))
    assert result["ok"] is True


def checkov(*failed):
    return {"results": {"failed_checks": [{"check_id": i, "file_path": f, "file_line_range": [1, 2]} for i, f in failed]}}


def test_no_failed_checks_is_compliant(policy):
    assert static_result(policy, checkov())["ok"] is True


def test_a_failed_check_at_a_fail_on_severity_makes_it_non_compliant(policy):
    result = static_result(policy, checkov(("CKV_DANTE_ANSIBLE_1", "/site.yml")))
    assert result["ok"] is False
    assert result["blocking"][0]["check_id"] == "CKV_DANTE_ANSIBLE_1"
    assert result["blocking"][0]["severity"] == "high"


def test_a_failed_check_below_fail_on_is_reported_but_not_blocking(policy):
    result = static_result(policy, checkov(("CKV2_ANSIBLE_3", "/site.yml")))
    assert result["ok"] is True
    assert result["advisory"][0]["check_id"] == "CKV2_ANSIBLE_3"


def test_a_failed_check_the_policy_does_not_enable_is_ignored(policy):
    result = static_result(policy, checkov(("CKV_ANSIBLE_999", "/site.yml")))
    assert result["ok"] is True and result["advisory"] == [] and result["blocking"] == []


def test_the_result_never_carries_anything_but_ids_files_and_lines(policy):
    raw = checkov(("CKV_DANTE_ANSIBLE_1", "/site.yml"))
    raw["results"]["failed_checks"][0]["code_block"] = [[1, "password: hunter2"]]
    result = static_result(policy, raw)
    assert "hunter2" not in repr(result)
