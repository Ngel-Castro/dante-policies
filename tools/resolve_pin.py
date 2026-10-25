"""Resolve a policy ref to a commit SHA. Tags and commits only, never branches.

Usage: python -m tools.resolve_pin <repo-url-or-path> <tag-or-sha>
Prints the 40-character commit SHA. Exit 1 with a reason when it cannot.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile

SHA = re.compile(r"^[0-9a-f]{40}$")


class PinError(Exception):
    pass


def _git(*args: str, cwd: str | None = None) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if done.returncode != 0:
        raise PinError(f"git {args[0]} failed: {done.stderr.strip().splitlines()[-1] if done.stderr.strip() else done.returncode}")
    return done.stdout


def resolve(repo: str, ref: str) -> str:
    if SHA.match(ref):
        with tempfile.TemporaryDirectory() as tmp:
            _git("init", "-q", tmp)
            try:
                _git("fetch", "-q", "--depth", "1", repo, ref, cwd=tmp)
            except PinError:
                raise PinError(f"commit {ref} not found in the repository")
            return _git("rev-parse", "FETCH_HEAD^{commit}", cwd=tmp).strip()

    listing = _git("ls-remote", repo, f"refs/tags/{ref}", f"refs/tags/{ref}^{{}}", f"refs/heads/{ref}")
    tags: dict[str, str] = {}
    branch = False
    for line in listing.splitlines():
        sha, name = line.split("\t")
        if name.startswith("refs/heads/"):
            branch = True
        elif name.endswith("^{}"):
            tags["peeled"] = sha
        else:
            tags["direct"] = sha
    if not tags:
        if branch:
            raise PinError(f"{ref} is a branch; pin a tag or a commit")
        raise PinError(f"{ref} not found as a tag")
    return tags.get("peeled") or tags["direct"]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        print(resolve(argv[0], argv[1]))
    except PinError as exc:
        print(f"cannot resolve {argv[1]}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
