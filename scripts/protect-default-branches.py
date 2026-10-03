#!/usr/bin/env python3
"""Make every repository's default branch impossible to delete or force-push.

    scripts/protect-default-branches.py                  # dry run over every repository of the org
    scripts/protect-default-branches.py --apply
    scripts/protect-default-branches.py --repo passioncode-ai/fabric --apply

Each repository gets one ruleset, "protect-default-branch": target ~DEFAULT_BRANCH, enforcement
active, rules `deletion` and `non_fast_forward`, no bypass actors. Ordinary pushes and merges are
untouched; requirements such as status checks stay each repository's own choice. Idempotent: an
existing ruleset of that name is updated only when it differs. Archived repositories are skipped.
A private repository on GitHub Free cannot hold rulesets ("Upgrade to GitHub Pro or make this
repository public"); it is reported as NOT PROTECTED, never as done. Operator decision 2026-10-03.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

NAME = "protect-default-branch"
DESIRED = {"name": NAME, "target": "branch", "enforcement": "active", "bypass_actors": [],
           "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
           "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]}


def gh(*args: str, body: dict | None = None) -> tuple[int, str]:
    feed = {"input": json.dumps(body)} if body is not None else {"stdin": subprocess.DEVNULL}
    p = subprocess.run(["gh", "api", *args, *(["--input", "-"] if body is not None else [])],
                       capture_output=True, text=True, **feed)
    return p.returncode, (p.stdout or p.stderr).strip()


def same(existing: dict) -> bool:
    rules = sorted(r.get("type") for r in existing.get("rules", []))
    inc = existing.get("conditions", {}).get("ref_name", {}).get("include", [])
    return (existing.get("enforcement") == "active" and rules == ["deletion", "non_fast_forward"]
            and inc == ["~DEFAULT_BRANCH"] and not existing.get("bypass_actors"))


def protect(repo: str, apply: bool) -> str:
    rc, out = gh(f"repos/{repo}/rulesets")
    if rc != 0:
        if "Upgrade to GitHub" in out:
            return "NOT PROTECTED: private repository on GitHub Free (needs Team/Pro or public visibility)"
        return f"NOT PROTECTED: cannot read rulesets ({out[:120]})"
    current = next((r for r in json.loads(out or "[]") if r.get("name") == NAME), None)
    if current:
        rc, detail = gh(f"repos/{repo}/rulesets/{current['id']}")
        if rc == 0 and same(json.loads(detail)):
            return "unchanged"
        if not apply:
            return "would update"
        rc, out = gh("-X", "PUT", f"repos/{repo}/rulesets/{current['id']}", body=DESIRED)
        return "updated" if rc == 0 else f"FAILED: {out[:160]}"
    if not apply:
        return "would create"
    rc, out = gh("-X", "POST", f"repos/{repo}/rulesets", body=DESIRED)
    return "created" if rc == 0 else f"FAILED: {out[:160]}"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--org", default="passioncode-ai")
    ap.add_argument("--repo", action="append", help="owner/name; repeatable; default: every repository of --org")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    if a.repo:
        repos = a.repo
    else:
        rc, out = gh(f"orgs/{a.org}/repos?per_page=100", "--paginate")
        if rc != 0:
            print(f"protect-default-branches: cannot list {a.org}: {out[:160]}", file=sys.stderr)
            return 2
        repos = sorted(f"{a.org}/{r['name']}" for r in json.loads(out) if not r.get("archived"))
    failed = unprotected = 0
    for repo in repos:
        verdict = protect(repo, a.apply)
        print(f"{repo}: {verdict}")
        failed += verdict.startswith("FAILED")
        unprotected += verdict.startswith("NOT PROTECTED")
    if not a.apply:
        print("dry run: nothing was changed; add --apply to write")
    print(f"{len(repos)} repositories; {unprotected} cannot be protected on this plan; {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
