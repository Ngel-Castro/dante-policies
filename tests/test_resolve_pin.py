import subprocess

import pytest

from tools.resolve_pin import PinError, resolve


def git(cwd, *args):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    ).stdout.strip()


@pytest.fixture
def origin(tmp_path):
    d = tmp_path / "origin"
    d.mkdir()
    git(d, "init", "-q", "-b", "main")
    (d / "f").write_text("1")
    git(d, "add", "f")
    git(d, "commit", "-q", "-m", "one")
    return d


def test_a_lightweight_tag_resolves_to_its_commit(origin):
    sha = git(origin, "rev-parse", "HEAD")
    git(origin, "tag", "v1")
    assert resolve(str(origin), "v1") == sha


def test_an_annotated_tag_resolves_to_the_commit_not_the_tag_object(origin):
    sha = git(origin, "rev-parse", "HEAD")
    git(origin, "tag", "-a", "v2", "-m", "release")
    assert resolve(str(origin), "v2") == sha


def test_a_branch_is_refused(origin):
    with pytest.raises(PinError, match="branch"):
        resolve(str(origin), "main")


def test_an_unknown_ref_is_refused(origin):
    with pytest.raises(PinError, match="not found"):
        resolve(str(origin), "v9")


def test_a_full_commit_sha_is_accepted_when_the_repository_has_it(origin):
    sha = git(origin, "rev-parse", "HEAD")
    assert resolve(str(origin), sha) == sha


def test_a_full_sha_the_repository_does_not_have_is_refused(origin):
    with pytest.raises(PinError, match="not found"):
        resolve(str(origin), "0" * 40)


def test_a_tag_moved_later_does_not_change_an_earlier_resolution(origin):
    first = resolve_after_tag(origin, "v1")
    (origin / "f").write_text("2")
    git(origin, "commit", "-q", "-am", "two")
    git(origin, "tag", "-f", "v1")
    assert resolve(str(origin), "v1") != first


def resolve_after_tag(origin, tag):
    git(origin, "tag", tag)
    return resolve(str(origin), tag)
