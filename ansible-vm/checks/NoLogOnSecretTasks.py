"""Custom checkov check for Ansible: a task that hands a secret-named variable
to a command-like module must set no_log: true, otherwise the value reaches the
run log. Backs the `no-secret-in-log` key characteristic."""
from __future__ import annotations

import re
from typing import Any

from checkov.ansible.checks.base_ansible_task_check import BaseAnsibleTaskCheck
from checkov.common.models.enums import CheckCategories, CheckResult
from checkov.yaml_doc.enums import BlockType

# A Jinja expression that mentions a variable whose name says it is a secret.
SECRET_REF = re.compile(r"\{\{[^}]*\b\w*(password|passwd|secret|token|api_key)\w*\b[^}]*\}\}", re.IGNORECASE)

MODULES = (
    "ansible.builtin.shell",
    "shell",
    "ansible.builtin.command",
    "command",
    "ansible.builtin.copy",
    "copy",
    "ansible.builtin.template",
    "template",
    "ansible.builtin.uri",
    "uri",
)


def _mentions_secret(value: Any) -> bool:
    if isinstance(value, str):
        return bool(SECRET_REF.search(value))
    if isinstance(value, dict):
        return any(_mentions_secret(v) for v in value.values())
    if isinstance(value, list):
        return any(_mentions_secret(v) for v in value)
    return False


class NoLogOnSecretTasks(BaseAnsibleTaskCheck):
    def __init__(self) -> None:
        super().__init__(
            name="Ensure tasks that pass a secret variable to a module set no_log: true",
            id="CKV_DANTE_ANSIBLE_1",
            categories=(CheckCategories.SECRETS,),
            supported_modules=MODULES,
            block_type=BlockType.ARRAY,
        )

    def scan_conf(self, conf: dict[str, Any]) -> tuple[CheckResult, dict[str, Any]]:
        if not _mentions_secret(conf):
            return CheckResult.PASSED, conf
        no_log = self.entity_conf.get("no_log")
        if no_log is True or (isinstance(no_log, str) and no_log.strip().lower() in ("true", "yes")):
            return CheckResult.PASSED, conf
        return CheckResult.FAILED, conf


check = NoLogOnSecretTasks()
