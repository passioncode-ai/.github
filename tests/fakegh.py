"""A fake `gh` for the release-signing scripts' tests.

It is written into a temporary bin directory as `gh`. Every call appends one JSON line to
$FAKE_GH_LOG: {"argv": [...], "stdin": "..."}. Answers come from $FAKE_GH_STATE, a JSON
file the test prepares: environments that exist, their policies, variables, the team id.
"""
from __future__ import annotations

import json
import os
import stat
import sys
import textwrap
from pathlib import Path

SCRIPT = textwrap.dedent('''\
    #!{python}
    import json, os, sys
    argv = sys.argv[1:]
    data = sys.stdin.read() if not sys.stdin.isatty() else ""
    with open(os.environ["FAKE_GH_LOG"], "a") as f:
        f.write(json.dumps({{"argv": argv, "stdin": data}}) + "\\n")
    state = json.load(open(os.environ["FAKE_GH_STATE"]))
    path = next((a for a in argv[1:] if not a.startswith("-") and "/" in a), "") if argv[:1] == ["api"] else ""
    method = argv[argv.index("-X") + 1] if "-X" in argv else "GET"
    if argv[:1] == ["api"]:
        if method == "GET" and path.startswith("repos/") and path.count("/") == 2:
            print(json.dumps({{"id": state.get("repo_id", 1389081624), "full_name": path[6:]}})); sys.exit(0)
        if method == "GET" and path.startswith("orgs/") and path.count("/") == 1:
            print(json.dumps({{"id": state.get("org_id", 320985480), "login": path[5:]}})); sys.exit(0)
        if path.startswith("orgs/") and "/teams/" in path and "/repos/" in path and method == "GET":
            repo = path.split("/repos/", 1)[1]
            if repo in state.get("team_repos", []):
                print(json.dumps({{"full_name": repo}})); sys.exit(0)
            print(json.dumps({{"message": "Not Found"}})); sys.exit(1)
        if path.startswith("orgs/") and "/teams/" in path and method == "GET":
            print(json.dumps({{"id": state.get("team_id", 7)}})); sys.exit(0)
        if path.endswith("/deployment-branch-policies") and method == "GET":
            print(json.dumps({{"branch_policies": state.get("policies", [])}})); sys.exit(0)
        if "/variables" in path and method == "GET":
            print(json.dumps({{"variables": state.get("variables", [])}})); sys.exit(0)
        if path.endswith("/environments/release") and method == "GET":
            if state.get("env"):
                print(json.dumps(state["env"])); sys.exit(0)
            print(json.dumps({{"message": "Not Found"}})); sys.exit(1)
        print("{{}}"); sys.exit(0)
    if argv[:2] == ["secret", "set"]:
        sys.exit(0)
    sys.exit(0)
    ''')


def install(tmp: Path, state: dict) -> dict[str, str]:
    bin_dir = tmp / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(SCRIPT.format(python=sys.executable))
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    (tmp / "state.json").write_text(json.dumps(state))
    return {"PATH": f"{bin_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}",
            "FAKE_GH_LOG": str(tmp / "calls.jsonl"), "FAKE_GH_STATE": str(tmp / "state.json")}


def calls(tmp: Path) -> list[dict]:
    log = tmp / "calls.jsonl"
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
