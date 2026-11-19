#!/usr/bin/env python3
"""Fail when the floating major tag does not point at the newest release of that major.

    scripts/check-floating-tag.py                 # reads the tags of origin, major 1
    scripts/check-floating-tag.py --remote <url-or-path> --major 1

Products call the shared actions at `@v1`, so a release `v1.X.Y` that does not move `v1` never
reaches them: `v1.3.2` and `v1.4.0` were tagged without moving `v1`, and a product release on
2026-11-04 still ran the old signing step (docs/backlog.md, ORGPROFILE-06). The check reads the
remote's tags with `git ls-remote --tags`, peels annotated tags to their commits, picks the
highest `vMAJOR.MINOR.PATCH` (pre-releases such as `v1.5.0-rc.1` are ignored) and compares it
with `vMAJOR`. Exit 0: in step; exit 1: lagging, missing or no release (the reason is printed);
exit 2: the tags could not be read, which is never reported as in step.

Run by the nightly self-test (.github/workflows/self-test.yml) and after every release.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

RELEASE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def peeled(ls_remote: str) -> dict[str, str]:
    """Tag name -> commit, preferring the peeled `^{}` line of an annotated tag."""
    tags: dict[str, str] = {}
    peeled_tags: dict[str, str] = {}
    for line in ls_remote.splitlines():
        parts = line.split()
        if len(parts) != 2 or not parts[1].startswith("refs/tags/"):
            continue
        sha, ref = parts
        name = ref.removeprefix("refs/tags/")
        if name.endswith("^{}"):
            peeled_tags[name[:-3]] = sha
        else:
            tags[name] = sha
    return {**tags, **peeled_tags}


def verdict(tags: dict[str, str], major: int) -> tuple[bool, str]:
    releases = sorted(
        ((tuple(int(x) for x in m.groups()), name) for name in tags if (m := RELEASE.match(name))
         and int(m.group(1)) == major),
    )
    floating = f"v{major}"
    if not releases:
        return False, f"no v{major}.X.Y release tag exists"
    newest = releases[-1][1]
    if floating not in tags:
        return False, f"{floating} is missing; it should point at {newest} ({tags[newest][:7]})"
    if tags[floating] != tags[newest]:
        behind = next((name for _, name in reversed(releases) if tags[name] == tags[floating]), None)
        where = f"{behind}" if behind else "a commit no release tag names"
        return False, (f"{floating} points at {tags[floating][:7]} ({where}), not at the newest release "
                       f"{newest} ({tags[newest][:7]}); move {floating} to {newest} "
                       "(release-signing/README.md, \"Rules for agents and people\")")
    return True, f"{floating} = {newest} ({tags[newest][:7]})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--major", type=int, default=1)
    args = parser.parse_args(argv)
    result = subprocess.run(["git", "ls-remote", "--tags", args.remote], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"floating tag: could not read the tags of {args.remote}: {result.stderr.strip()}", file=sys.stderr)
        return 2
    ok, reason = verdict(peeled(result.stdout), args.major)
    print(f"floating tag: {'in step' if ok else 'NOT IN STEP'}: {reason}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
