import re

import yaml

from tools.lint_policy import lint


def edit(repo, fn):
    path = repo / "ansible-vm" / "policy.yaml"
    data = yaml.safe_load(path.read_text())
    fn(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def test_the_shipped_policy_is_valid(repo):
    assert lint(repo / "ansible-vm" / "policy.yaml", repo) == []


def test_duplicate_characteristic_id_is_reported(repo):
    edit(repo, lambda d: d["characteristics"].append(dict(d["characteristics"][0])))
    errors = lint(repo / "ansible-vm" / "policy.yaml", repo)
    assert any("duplicate characteristic id" in e for e in errors)


def test_unknown_severity_is_reported(repo):
    edit(repo, lambda d: d["static_checks"]["checks"][0].update(severity="urgent"))
    assert lint(repo / "ansible-vm" / "policy.yaml", repo)


def test_characteristic_id_must_be_kebab_case(repo):
    edit(repo, lambda d: d["characteristics"][0].update(id="Linked_Secrets"))
    assert lint(repo / "ansible-vm" / "policy.yaml", repo)


def test_fail_on_must_name_known_severities(repo):
    edit(repo, lambda d: d["static_checks"].update(fail_on=["blocker"]))
    assert lint(repo / "ansible-vm" / "policy.yaml", repo)


def test_duplicate_check_id_is_reported(repo):
    edit(repo, lambda d: d["static_checks"]["checks"].append(dict(d["static_checks"]["checks"][0])))
    errors = lint(repo / "ansible-vm" / "policy.yaml", repo)
    assert any("duplicate check id" in e for e in errors)


def test_a_custom_check_the_policy_names_must_exist_as_code(repo):
    edit(repo, lambda d: d["static_checks"]["checks"].append({"id": "CKV_DANTE_ANSIBLE_99", "severity": "low"}))
    errors = lint(repo / "ansible-vm" / "policy.yaml", repo)
    assert any("CKV_DANTE_ANSIBLE_99" in e and "no check" in e for e in errors)


def test_a_custom_check_in_code_the_policy_does_not_enable_is_reported(repo):
    (repo / "ansible-vm" / "checks" / "extra.yaml").write_text(
        'metadata:\n  id: "CKV_DANTE_ANSIBLE_50"\n  name: "x"\n  category: "GENERAL_SECURITY"\n'
        "definition:\n  cond_type: attribute\n  resource_types: [tasks.copy]\n  attribute: mode\n  operator: exists\n"
    )
    errors = lint(repo / "ansible-vm" / "policy.yaml", repo)
    assert any("CKV_DANTE_ANSIBLE_50" in e and "not enabled" in e for e in errors)


def test_a_file_that_is_not_yaml_is_reported_not_raised(repo):
    (repo / "ansible-vm" / "policy.yaml").write_text("a: [unclosed")
    errors = lint(repo / "ansible-vm" / "policy.yaml", repo)
    assert errors and re.search("yaml", errors[0], re.I)
