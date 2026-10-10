#!/usr/bin/env python3
"""Create or update a product repository's `release` environment as the design names it.

    scripts/setup-release-env.py --repo passioncode-ai/fabric-dashboards          # dry run
    scripts/setup-release-env.py --all --apply

For each repository in release-signing/products.json:
  * reviewers = the team named in the manifest (release-approvers);
  * prevent_self_review from the manifest (false since 2026-10-03: any team member may approve,
    the tag's author included; true restores four eyes);
  * can_admins_bypass = false: an organization admin cannot skip the review either;
  * deployments only from tags matching the manifest's pattern (`v*`);
  * the repository's environment variables (APPLE_TEAM_ID, AZURE_SIGNING_ENABLED, …), and for a
    repository with "windows": true the shared Artifact Signing account's AZURE_SIGNING_ENDPOINT,
    AZURE_SIGNING_ACCOUNT and AZURE_CERTIFICATE_PROFILE (its own Azure identity is
    scripts/setup-windows-signing.py's).

A dry run reads and prints the plan; --apply writes. Running it twice changes nothing the
second time. Secrets are not handled here: scripts/sync-release-secrets.py sets them.
Design: docs/release-signing/DESIGN.md.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "release-signing" / "products.json"


def gh(*args: str, body: dict | None = None, check: bool = True) -> dict | None:
    # Without a body, gh gets an empty stdin rather than inheriting ours: a caller's open stdin
    # would otherwise be read (and waited on) by anything downstream that reads it.
    feed = {"input": json.dumps(body)} if body is not None else {"stdin": subprocess.DEVNULL}
    proc = subprocess.run(["gh", "api", *args, *(["--input", "-"] if body is not None else [])],
                          capture_output=True, text=True, **feed)
    if proc.returncode != 0:
        if check:
            raise SystemExit(f"setup-release-env: gh api {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}")
        return None
    return json.loads(proc.stdout or "{}")


def desired_env(team_id: int, self_review_blocked: bool) -> dict:
    return {"wait_timer": 0, "prevent_self_review": self_review_blocked, "can_admins_bypass": False,
            "reviewers": [{"type": "Team", "id": team_id}],
            "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True}}


def env_matches(current: dict | None, team_id: int, self_review_blocked: bool) -> bool:
    if not current:
        return False
    rules = {r.get("type"): r for r in current.get("protection_rules", [])}
    reviewers = rules.get("required_reviewers", {})
    ids = [(r.get("type"), (r.get("reviewer") or {}).get("id")) for r in reviewers.get("reviewers", [])]
    return (ids == [("Team", team_id)] and reviewers.get("prevent_self_review") is self_review_blocked
            and current.get("can_admins_bypass") is False
            and current.get("deployment_branch_policy") == {"protected_branches": False, "custom_branch_policies": True})


def desired_vars(conf: dict, manifest: dict) -> dict[str, str]:
    wanted = {}
    if conf.get("windows"):
        azure = manifest["azure_signing"]
        wanted = {"AZURE_SIGNING_ENDPOINT": azure["endpoint"], "AZURE_SIGNING_ACCOUNT": azure["account"],
                  "AZURE_CERTIFICATE_PROFILE": azure["certificate_profile"]}
    out = dict(conf.get("vars", {}))  # the repository's own first; its value wins
    for name, value in wanted.items():
        out.setdefault(name, value)
    return out


def setup(repo: str, conf: dict, manifest: dict, team_id: int, apply: bool) -> list[str]:
    env_name, pattern = manifest["environment"], manifest["tag_pattern"]
    base = f"repos/{repo}/environments/{env_name}"
    lines: list[str] = []

    def act(what: str, fn) -> None:
        lines.append(("" if apply else "would ") + what)
        if apply:
            fn()

    # GitHub accepts a team as a required reviewer only when the team itself has access to the
    # repository, public or not (measured 2026-10-03: HTTP 422 "Required reviewers must have at
    # least one reviewer" until it did). Read access is enough to approve a deployment.
    org, name = repo.split("/")
    team_repo = f"orgs/{org}/teams/{manifest['team']}/repos/{repo}"
    if gh(team_repo, check=False) is not None:
        lines.append(f"team {manifest['team']} access: unchanged")
    else:
        act(f"give team {manifest['team']} read access to {name}",
            lambda: gh("-X", "PUT", team_repo, body={"permission": "pull"}))

    # The operator's decision (D5, amended 2026-10-03): a member of the team may approve a
    # release they started. The manifest's `prevent_self_review` carries it; true restores the
    # four-eyes rule.
    blocked = bool(manifest.get("prevent_self_review", True))
    current = gh(base, check=False)
    if env_matches(current, team_id, blocked):
        lines.append(f"environment {env_name}: unchanged")
    else:
        act(f"set environment {env_name}: reviewers team {manifest['team']}, "
            f"{'no self-review' if blocked else 'self-review allowed'}, no admin bypass, tags only",
            lambda: gh("-X", "PUT", base, body=desired_env(team_id, blocked)))

    policies = (gh(f"{base}/deployment-branch-policies", check=False) or {}).get("branch_policies", [])
    if any(p.get("name") == pattern and p.get("type") == "tag" for p in policies):
        lines.append(f"tag policy {pattern}: unchanged")
    else:
        act(f"add tag policy {pattern}",
            lambda: gh("-X", "POST", f"{base}/deployment-branch-policies", body={"name": pattern, "type": "tag"}))

    existing = {v["name"]: v.get("value") for v in (gh(f"{base}/variables", check=False) or {}).get("variables", [])}
    for name, value in desired_vars(conf, manifest).items():
        if existing.get(name) == value:
            lines.append(f"variable {name}: unchanged")
        elif name in existing:
            act(f"update variable {name}={value}",
                lambda n=name, v=value: gh("-X", "PATCH", f"{base}/variables/{n}", body={"name": n, "value": v}))
        else:
            act(f"create variable {name}={value}",
                lambda n=name, v=value: gh("-X", "POST", f"{base}/variables", body={"name": n, "value": v}))
    return lines


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--repo", action="append", help="owner/name, repeatable")
    target.add_argument("--all", action="store_true", help="every repository in the manifest")
    parser.add_argument("--apply", action="store_true", help="write; without it, a dry run")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args(argv)

    manifest = json.loads(args.manifest.read_text())
    repos = list(manifest["repos"]) if args.all else args.repo
    unknown = [r for r in repos if r not in manifest["repos"]]
    if unknown:
        print(f"setup-release-env: not in {args.manifest.name}: {', '.join(unknown)}", file=sys.stderr)
        return 2
    org = repos[0].split("/")[0]
    team_id = gh(f"orgs/{org}/teams/{manifest['team']}")["id"]
    for repo in repos:
        print(repo)
        for line in setup(repo, manifest["repos"][repo], manifest, team_id, args.apply):
            print("  " + line)
    if not args.apply:
        print("dry run: nothing was changed; add --apply to write")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
