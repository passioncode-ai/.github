#!/usr/bin/env python3
"""The release guard: a tag release goes on only when the tag is on main and its CI passed.

It replaces a person's approval of the `release` environment (docs/release-signing/DESIGN.md,
"Approval by checks", operator 2026-10-11). Run by actions/release-guard in a product's `guard`
job; every job that names `environment: release` needs that job.

Environment (set by action.yml): REPO, REF, SHA, MAIN, WORKFLOWS (one file name per line, may be
empty), DISPATCH ("true" to start a workflow on the tag when none ran on the commit),
TIMEOUT_MINUTES, POLL_SECONDS, GRACE_SECONDS, and GH_TOKEN for `gh`.

Checks, in order, each one failing the job with what to do:
  1. the run publishes (PUBLISH, default "true") and its ref is a tag; a rehearsal — a run with
     publish=false, or any ref that is not a tag, which the environment's tag policy keeps away from
     the keys anyway — publishes nothing, and passes with a notice (only the team can push even an
     `-rc` tag, by the release-tags ruleset);
  2. main contains the tagged commit (the compare API: `identical` or main `ahead`);
  3. for each listed workflow, its newest run on that exact commit concluded `success`; with no
     run after GRACE_SECONDS, or with the newest run cancelled (cancel-in-progress on main), the
     guard starts one on the tag (workflow_dispatch) once when DISPATCH is on, and waits up to
     TIMEOUT_MINUTES for it.
An empty WORKFLOWS list means the release workflow runs its own gate before signing; only the
ancestry check applies then.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time


def gh(*args: str) -> dict:
    proc = subprocess.run(["gh", "api", *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if proc.returncode != 0:
        raise RuntimeError(f"gh api {' '.join(args)}: {(proc.stderr or proc.stdout).strip()}")
    return json.loads(proc.stdout or "{}")


def summary(line: str) -> None:
    print(line)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def fail(message: str) -> int:
    print(f"::error title=release guard::{message}")
    summary(f"release guard: refused — {message}")
    return 1


def newest_run(repo: str, workflow: str, sha: str) -> dict | None:
    runs = gh(f"repos/{repo}/actions/workflows/{workflow}/runs?head_sha={sha}&per_page=20").get("workflow_runs", [])
    return max(runs, key=lambda r: r.get("created_at", ""), default=None)


def wait_for(repo: str, workflow: str, sha: str, tag: str, *, dispatch: bool, deadline: float,
             poll: float, grace: float, started: float) -> str | None:
    """None when the workflow passed on `sha`, else the reason it did not."""
    dispatched = False
    while True:
        run = newest_run(repo, workflow, sha)
        if run is None:
            if dispatch and not dispatched and time.monotonic() - started >= grace:
                gh("-X", "POST", f"repos/{repo}/actions/workflows/{workflow}/dispatches", "-f", f"ref={tag}")
                dispatched = True
                print(f"{workflow}: no run on {sha[:7]}; started one on {tag}")
        elif run.get("status") == "completed" and run.get("conclusion") == "cancelled" and dispatch and not dispatched:
            # A CI with cancel-in-progress loses the tagged commit's run to the next push on main;
            # a run on the tag is in its own concurrency group, so start one there, once.
            gh("-X", "POST", f"repos/{repo}/actions/workflows/{workflow}/dispatches", "-f", f"ref={tag}")
            dispatched = True
            print(f"{workflow}: the run on {sha[:7]} was cancelled; started one on {tag}")
        elif run.get("status") == "completed":
            if run.get("conclusion") == "success":
                summary(f"- {workflow}: success on {sha[:7]} ({run.get('html_url', '')})")
                return None
            return (f"{workflow} concluded {run.get('conclusion')} on {sha[:7]} ({run.get('html_url', '')}); "
                    "fix it, let it pass on this commit, then re-run this release")
        if time.monotonic() >= deadline:
            state = "never ran" if run is None else f"is still {run.get('status')}"
            return f"{workflow} {state} on {sha[:7]} within the time limit; re-run this release once it has passed"
        time.sleep(poll)


def main() -> int:
    repo, ref, sha = os.environ["REPO"], os.environ["REF"], os.environ["SHA"]
    main_branch = os.environ.get("MAIN") or "main"
    workflows = [w.strip() for w in os.environ.get("WORKFLOWS", "").splitlines() if w.strip()]
    dispatch = os.environ.get("DISPATCH", "true").lower() == "true"
    timeout = float(os.environ.get("TIMEOUT_MINUTES") or 60) * 60
    poll = float(os.environ.get("POLL_SECONDS") or 30)
    grace = float(os.environ.get("GRACE_SECONDS") or 120)

    if os.environ.get("PUBLISH", "true").lower() != "true":
        print(f"::notice title=release guard::{ref}: a rehearsal (publish=false); nothing is published, so "
              "main and CI are not required")
        return 0
    if not ref.startswith("refs/tags/"):
        print(f"::notice title=release guard::{ref} is not a tag: a rehearsal; the release environment's "
              "tag policy keeps the signing keys away from it")
        return 0
    tag = ref.removeprefix("refs/tags/")
    started = time.monotonic()
    try:
        status = gh(f"repos/{repo}/compare/{sha}...{main_branch}").get("status")
        if status not in ("identical", "ahead"):
            return fail(f"{tag} ({sha[:7]}) is not on {main_branch} (compare: {status}); "
                        f"tag a commit that {main_branch} contains")
        summary(f"release guard: {tag} ({sha[:7]}) is on {main_branch}")
        for workflow in workflows:
            reason = wait_for(repo, workflow, sha, tag, dispatch=dispatch, deadline=started + timeout,
                              poll=poll, grace=grace, started=started)
            if reason:
                return fail(reason)
    except RuntimeError as exc:
        return fail(f"GitHub could not answer: {exc}")
    if not workflows:
        summary("- no CI workflow listed: the release workflow's own gate runs before signing")
    summary(f"release guard: {tag} may sign and publish")
    return 0


if __name__ == "__main__":
    sys.exit(main())
