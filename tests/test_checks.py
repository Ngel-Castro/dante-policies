"""Run the custom checks through checkov itself, on small playbooks."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CHECKOV = shutil.which("checkov", path=str(Path(sys.executable).parent)) or shutil.which("checkov")
pytestmark = pytest.mark.skipif(CHECKOV is None, reason="checkov is not installed")


def run(tmp_path, playbook: str) -> list[str]:
    (tmp_path / "site.yml").write_text(playbook)
    done = subprocess.run(
        [CHECKOV, "-d", str(tmp_path), "--framework", "ansible",
         "--external-checks-dir", str(ROOT / "ansible-vm" / "checks"), "--quiet", "-o", "json"],
        capture_output=True, text=True,
    )
    data = json.loads(done.stdout)
    data = data[0] if isinstance(data, list) else data
    return sorted(f["check_id"] for f in data["results"]["failed_checks"] if f["check_id"].startswith("CKV_DANTE_"))


def play(task: str) -> str:
    return "- hosts: all\n  tasks:\n" + "".join("    " + line + "\n" for line in task.strip().splitlines())


def test_secret_variable_in_a_shell_task_without_no_log_fails(tmp_path):
    task = '- name: set it\n  ansible.builtin.shell:\n    cmd: "psql -c \\"ALTER USER x PASSWORD \'{{ db_password }}\'\\""'
    assert run(tmp_path, play(task)) == ["CKV_DANTE_ANSIBLE_1"]


def test_the_same_task_with_no_log_passes(tmp_path):
    task = '- name: set it\n  no_log: true\n  ansible.builtin.shell:\n    cmd: "psql -c \\"ALTER USER x PASSWORD \'{{ db_password }}\'\\""'
    assert run(tmp_path, play(task)) == []


def test_a_task_that_mentions_no_secret_variable_needs_no_no_log(tmp_path):
    task = '- name: hello\n  ansible.builtin.copy:\n    dest: /tmp/x\n    content: "{{ greeting }}"'
    assert run(tmp_path, play(task)) == []


def test_a_secret_in_copy_content_without_no_log_fails(tmp_path):
    task = "- name: write it\n  ansible.builtin.copy:\n    dest: /tmp/x\n    content: \"TOKEN={{ lookup('env', 'GITHUB_TOKEN') }}\""
    assert run(tmp_path, play(task)) == ["CKV_DANTE_ANSIBLE_1"]


def test_no_log_false_is_not_accepted(tmp_path):
    task = '- name: set it\n  no_log: false\n  ansible.builtin.command:\n    cmd: "login {{ api_token }}"'
    assert run(tmp_path, play(task)) == ["CKV_DANTE_ANSIBLE_1"]


def test_get_url_without_a_timeout_fails_the_yaml_check(tmp_path):
    task = "- name: get\n  ansible.builtin.get_url:\n    url: https://example.test/a\n    dest: /tmp/a"
    assert run(tmp_path, play(task)) == ["CKV_DANTE_ANSIBLE_2"]


def test_get_url_with_a_timeout_passes_the_yaml_check(tmp_path):
    task = "- name: get\n  ansible.builtin.get_url:\n    url: https://example.test/a\n    dest: /tmp/a\n    timeout: 30"
    assert run(tmp_path, play(task)) == []
