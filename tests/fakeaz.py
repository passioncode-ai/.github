"""A fake `az` for scripts/setup-windows-signing.py's tests.

Written into a temporary bin directory as `az`. Every call appends one JSON line to
$FAKE_AZ_LOG ({"argv": [...]}). State lives in $FAKE_AZ_STATE and persists between calls, so a
second run sees what the first created: apps, service principals, federated credentials and role
assignments.
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
    with open(os.environ["FAKE_AZ_LOG"], "a") as f:
        f.write(json.dumps({{"argv": argv}}) + "\\n")
    path = os.environ["FAKE_AZ_STATE"]
    s = json.load(open(path))
    def opt(name):
        return argv[argv.index(name) + 1] if name in argv else None
    def out(obj):
        json.dump(s, open(path, "w")); print(json.dumps(obj)); sys.exit(0)
    def fail(msg, code=3):
        json.dump(s, open(path, "w")); print(msg, file=sys.stderr); sys.exit(code)
    if s.get("expired"):
        fail("AADSTS50132: The session is not valid", 1)
    head = argv[:3]
    if argv[:2] == ["account", "show"]:
        out({{"tenantId": s["tenant"], "id": s["subscription"]}})
    if argv[:2] == ["resource", "show"]:
        name = opt("--name") or opt("-n")
        if name in s.get("accounts", {{}}):
            out({{"id": s["accounts"][name]}})
        fail("ResourceNotFound")
    apps = s.setdefault("apps", [])
    if head == ["ad", "app", "list"]:
        # Like Graph's filter behind `az ad app list --display-name`: startswith, not equality.
        out([a for a in apps if a["displayName"].startswith(opt("--display-name"))])
    if head == ["ad", "app", "show"]:
        hit = [a for a in apps if a["appId"] == opt("--id")]
        out(hit[0]) if hit else fail("Resource does not exist")
    if head == ["ad", "app", "create"]:
        n = len(apps) + 1
        app = {{"appId": f"00000000-0000-0000-0000-00000000000{{n}}", "id": f"obj-app-{{n}}", "displayName": opt("--display-name"), "fic": []}}
        apps.append(app); out(app)
    sps = s.setdefault("sps", {{}})
    if head == ["ad", "sp", "show"]:
        sp = sps.get(opt("--id"))
        out(sp) if sp else fail("Resource does not exist")
    if head == ["ad", "sp", "create"]:
        sp = {{"id": "sp-" + opt("--id")[-1], "appId": opt("--id")}}
        sps[opt("--id")] = sp; out(sp)
    if argv[:4] == ["ad", "app", "federated-credential", "list"]:
        app = [a for a in apps if a["appId"] == opt("--id")][0]
        out(app["fic"])
    if argv[:4] == ["ad", "app", "federated-credential", "create"]:
        app = [a for a in apps if a["appId"] == opt("--id")][0]
        fic = json.loads(opt("--parameters")); app["fic"].append(fic); out(fic)
    roles = s.setdefault("roles", [])
    if argv[:3] == ["role", "assignment", "list"]:
        out([r for r in roles if r["principalId"] == opt("--assignee") and r["scope"] == opt("--scope") and r["roleDefinitionName"] == opt("--role")])
    if argv[:3] == ["role", "assignment", "create"]:
        r = {{"principalId": opt("--assignee-object-id"), "principalType": opt("--assignee-principal-type"), "scope": opt("--scope"), "roleDefinitionName": opt("--role")}}
        roles.append(r); out(r)
    fail("fake az: unknown command " + " ".join(argv), 2)
    ''')



def install(tmp: Path, state: dict) -> dict[str, str]:
    bin_dir = tmp / "bin"
    bin_dir.mkdir(exist_ok=True)
    az = bin_dir / "az"
    az.write_text(SCRIPT.format(python=sys.executable))
    az.chmod(az.stat().st_mode | stat.S_IXUSR)
    (tmp / "az-state.json").write_text(json.dumps(state))
    return {"FAKE_AZ_LOG": str(tmp / "az-calls.jsonl"), "FAKE_AZ_STATE": str(tmp / "az-state.json")}


def calls(tmp: Path) -> list[list[str]]:
    log = tmp / "az-calls.jsonl"
    return [json.loads(line)["argv"] for line in log.read_text().splitlines()] if log.exists() else []


def creates(tmp: Path) -> list[list[str]]:
    return [a for a in calls(tmp) if "create" in a]


def state(tmp: Path) -> dict:
    return json.loads((tmp / "az-state.json").read_text())
