#!/usr/bin/env python3
"""Make this repository's release tags impossible to delete, and every `vX.Y.Z` impossible to move.

    scripts/protect-release-tags.py                      # dry run on passioncode-ai/.github
    scripts/protect-release-tags.py --apply

Products call the shared actions at `@v1` from release jobs that see the signing secrets, so a
moved or deleted tag here changes what those jobs run. Three tag rulesets, enforcement active:

- `release-tags-no-deletion`: `refs/tags/v*`, rule `deletion`, no bypass. No `v*` tag is deleted,
  `v1` included.
- `release-tags-immutable`: `refs/tags/v*` except `refs/tags/v1`, rule `update`, no bypass. A
  published `vX.Y.Z` never moves; a wrong release is a new tag.
- `floating-major-tag`: `refs/tags/v1`, rule `update`, bypass: organization admins only. Only an
  organization admin moves `v1`, and only to a commit that already carries a `v1.X.Y` tag with a
  green self-test (release-signing/README.md, "Rules for agents and people").

Creating a new tag stays open. Idempotent: an existing ruleset of the same name is updated only
when it differs. Requested by org-index (decision D1, condition C1, board request d60fc7ca,
2026-11-14).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

TAGS = "refs/tags/v*"
FLOATING = "refs/tags/v1"
ADMINS = {"actor_id": 1, "actor_type": "OrganizationAdmin", "bypass_mode": "always"}


def ruleset(name: str, include: list[str], exclude: list[str], rule: str, bypass: list[dict]) -> dict:
    return {"name": name, "target": "tag", "enforcement": "active", "bypass_actors": bypass,
            "conditions": {"ref_name": {"include": include, "exclude": exclude}},
            "rules": [{"type": rule}]}


DESIRED = [
    ruleset("release-tags-no-deletion", [TAGS], [], "deletion", []),
    ruleset("release-tags-immutable", [TAGS], [FLOATING], "update", []),
    ruleset("floating-major-tag", [FLOATING], [], "update", [ADMINS]),
]


def gh(*args: str, body: dict | None = None) -> tuple[int, str]:
    feed = {"input": json.dumps(body)} if body is not None else {"stdin": subprocess.DEVNULL}
    p = subprocess.run(["gh", "api", *args, *(["--input", "-"] if body is not None else [])],
                       capture_output=True, text=True, **feed)
    return p.returncode, (p.stdout or p.stderr).strip()


def same(existing: dict, want: dict) -> bool:
    cond = existing.get("conditions", {}).get("ref_name", {})
    bypass = sorted((b.get("actor_type"), b.get("bypass_mode")) for b in existing.get("bypass_actors") or [])
    return (existing.get("target") == "tag" and existing.get("enforcement") == "active"
            and sorted(r.get("type") for r in existing.get("rules", [])) == [r["type"] for r in want["rules"]]
            and sorted(cond.get("include", [])) == sorted(want["conditions"]["ref_name"]["include"])
            and sorted(cond.get("exclude", [])) == sorted(want["conditions"]["ref_name"]["exclude"])
            and bypass == sorted((b["actor_type"], b["bypass_mode"]) for b in want["bypass_actors"]))


def protect(repo: str, apply: bool) -> list[str]:
    rc, out = gh(f"repos/{repo}/rulesets")
    if rc != 0:
        if "Upgrade to GitHub" in out:
            return ["NOT PROTECTED: private repository on GitHub Free (needs Team/Pro or public visibility)"]
        return [f"NOT PROTECTED: cannot read rulesets ({out[:120]})"]
    existing = {r.get("name"): r for r in json.loads(out or "[]")}
    verdicts = []
    for want in DESIRED:
        current = existing.get(want["name"])
        if current:
            rc, detail = gh(f"repos/{repo}/rulesets/{current['id']}")
            if rc == 0 and same(json.loads(detail), want):
                verdicts.append(f"{want['name']} ({current['id']}): unchanged")
                continue
            if not apply:
                verdicts.append(f"{want['name']} ({current['id']}): would update")
                continue
            rc, out = gh("-X", "PUT", f"repos/{repo}/rulesets/{current['id']}", body=want)
            verdicts.append(f"{want['name']} ({current['id']}): " + ("updated" if rc == 0 else f"FAILED: {out[:160]}"))
            continue
        if not apply:
            verdicts.append(f"{want['name']}: would create")
            continue
        rc, out = gh("-X", "POST", f"repos/{repo}/rulesets", body=want)
        if rc != 0:
            verdicts.append(f"{want['name']}: FAILED: {out[:160]}")
            continue
        verdicts.append(f"{want['name']} ({json.loads(out or '{}').get('id', '?')}): created")
    return verdicts


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", action="append", help="owner/name; repeatable; default: passioncode-ai/.github")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    failed = unprotected = 0
    for repo in a.repo or ["passioncode-ai/.github"]:
        for verdict in protect(repo, a.apply):
            print(f"{repo}: {verdict}")
            failed += "FAILED" in verdict
            unprotected += verdict.startswith("NOT PROTECTED")
    if not a.apply:
        print("dry run: nothing was changed; add --apply to write")
    return 1 if failed or unprotected else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
