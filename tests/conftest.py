import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def repo(tmp_path):
    """A throwaway copy of the policy repository to mutate in tests."""
    dest = tmp_path / "repo"
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    return dest
