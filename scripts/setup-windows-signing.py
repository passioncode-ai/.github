#!/usr/bin/env python3
"""Give a product repository its own Azure identity for Windows signing, bound to its `release` environment.

    scripts/setup-windows-signing.py --repo passioncode-ai/project-observatory-dashboard          # dry run
    scripts/setup-windows-signing.py --repo passioncode-ai/project-observatory-dashboard --apply

Runs under the operator's `az login` (Entra ID and the subscription that holds the Artifact
Signing account named in release-signing/products.json → azure_signing) and `gh` with admin on
the repository. For the repository it makes, only where missing:

  * an app registration `<app_prefix><repo name>` and its service principal — unless the
    environment's AZURE_CLIENT_ID already names an app, which is then kept (identities made by
    hand before this script);
  * federated credentials for that environment only, issuer GitHub Actions, audience
    `api://AzureADTokenExchange`, in both subject forms GitHub uses: the immutable one,
    `repo:<owner>@<owner id>/<repo>@<repo id>:environment:release` (what GitHub presents since
    2026: Switchboard's first signed run, 2026-10-10, failed at azure/login with AADSTS700213
    "No matching federated identity record" holding only the other), and the name form
    `repo:<owner>/<repo>:environment:release`. Tokens go only to jobs in that environment, and no
    client secret exists;
  * one role assignment, `azure_signing.role` on the Artifact Signing account and nothing broader;
  * the environment variables AZURE_CLIENT_ID, AZURE_TENANT_ID and AZURE_SUBSCRIPTION_ID.

The account's own variables (endpoint, account, profile) and AZURE_SIGNING_ENABLED are
setup-release-env.py's. A dry run reads and prints the plan; --apply writes; a second run
changes nothing. The values printed are identifiers, not secrets. Usage:
release-signing/README.md → Windows.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "release-signing" / "products.json"
ISSUER = "https://token.actions.githubusercontent.com"
AUDIENCE = "api://AzureADTokenExchange"


class AzError(SystemExit):
    pass


def az(*args: str, missing_ok: bool = False):
    proc = subprocess.run(["az", *args, "-o", "json"], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout).strip()
        if "AADSTS" in err or "az login" in err:
            raise AzError("setup-windows-signing: the az session is not valid; the operator signs in with "
                          "`az login --scope https://graph.microsoft.com//.default` and runs this again "
                          f"({err.splitlines()[0][:160]})")
        if missing_ok:
            return None
        raise AzError(f"setup-windows-signing: az {' '.join(args[:4])} failed: {err[:400]}")
    return json.loads(proc.stdout or "null")


def gh(*args: str, body: dict | None = None, check: bool = True):
    feed = {"input": json.dumps(body)} if body is not None else {"stdin": subprocess.DEVNULL}
    proc = subprocess.run(["gh", "api", *args, *(["--input", "-"] if body is not None else [])],
                          capture_output=True, text=True, **feed)
    if proc.returncode != 0:
        if check:
            raise SystemExit(f"setup-windows-signing: gh api {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}")
        return None
    return json.loads(proc.stdout or "{}")


def subjects(repo: str, env_name: str) -> list[tuple[str, str]]:
    """The OIDC subjects a job in `env_name` of `repo` may present: immutable ids first."""
    owner, name = repo.split("/")
    owner_id = gh(f"orgs/{owner}")["id"]
    repo_id = gh(f"repos/{repo}")["id"]
    return [(f"repo:{owner}@{owner_id}/{name}@{repo_id}:environment:{env_name}", "-ids"),
            (f"repo:{repo}:environment:{env_name}", "")]


def setup(repo: str, manifest: dict, apply: bool) -> list[str]:
    azure = manifest["azure_signing"]
    env_name = manifest["environment"]
    base = f"repos/{repo}/environments/{env_name}"
    lines: list[str] = []
    prefix = "" if apply else "would "

    account = az("account", "show")
    tenant, subscription = account["tenantId"], account["id"]
    found = az("resource", "show", "--resource-group", azure["resource_group"], "--name", azure["account"],
               "--resource-type", "Microsoft.CodeSigning/codeSigningAccounts", missing_ok=True)
    if not found:
        raise AzError(f"setup-windows-signing: the Artifact Signing account {azure['account']} is not in "
                      f"resource group {azure['resource_group']} of the subscription az is signed in to")
    scope = found["id"]

    existing = {v["name"]: v.get("value") for v in (gh(f"{base}/variables", check=False) or {}).get("variables", [])}
    app = None
    if existing.get("AZURE_CLIENT_ID"):
        app = az("ad", "app", "show", "--id", existing["AZURE_CLIENT_ID"], missing_ok=True)
        if app:
            lines.append(f"app registration {app['displayName']} ({app['appId']}): kept, named by AZURE_CLIENT_ID")
    name = azure["app_prefix"] + repo.split("/")[1]
    if not app:
        hits = az("ad", "app", "list", "--display-name", name)
        if hits:
            app = hits[0]
            lines.append(f"app registration {name} ({app['appId']}): unchanged")
        else:
            lines.append(f"{prefix}create app registration {name}")
            if not apply:
                app = {"appId": "<new>", "displayName": name}
            else:
                app = az("ad", "app", "create", "--display-name", name, "--sign-in-audience", "AzureADMyOrg")
    app_id = app["appId"]

    sp = az("ad", "sp", "show", "--id", app_id, missing_ok=True) if app_id != "<new>" else None
    if sp:
        lines.append("service principal: unchanged")
    else:
        lines.append(f"{prefix}create its service principal")
        sp = az("ad", "sp", "create", "--id", app_id) if apply else {"id": "<new>"}

    fics = az("ad", "app", "federated-credential", "list", "--id", app_id) if app_id != "<new>" else []
    for subject, suffix in subjects(repo, env_name):
        if any(f.get("subject") == subject and f.get("issuer") == ISSUER for f in fics):
            lines.append(f"federated credential {subject}: unchanged")
            continue
        lines.append(f"{prefix}add federated credential {subject}")
        if apply:
            params = {"name": f"github-{repo.split('/')[1]}-{env_name}{suffix}", "issuer": ISSUER, "subject": subject,
                      "audiences": [AUDIENCE], "description": "GitHub Actions release environment (setup-windows-signing.py)"}
            az("ad", "app", "federated-credential", "create", "--id", app_id, "--parameters", json.dumps(params))

    roles = az("role", "assignment", "list", "--assignee", sp["id"], "--scope", scope, "--role", azure["role"]) \
        if sp["id"] != "<new>" else []
    if roles:
        lines.append(f"role {azure['role']} on {azure['account']}: unchanged")
    else:
        lines.append(f"{prefix}assign {azure['role']} on {azure['account']} to the service principal")
        if apply:
            az("role", "assignment", "create", "--assignee-object-id", sp["id"], "--assignee-principal-type",
               "ServicePrincipal", "--role", azure["role"], "--scope", scope)

    for var, value in (("AZURE_CLIENT_ID", app_id), ("AZURE_TENANT_ID", tenant), ("AZURE_SUBSCRIPTION_ID", subscription)):
        if existing.get(var) == value:
            lines.append(f"variable {var}: unchanged")
        elif var in existing:
            lines.append(f"{prefix}update variable {var}={value}")
            if apply:
                gh("-X", "PATCH", f"{base}/variables/{var}", body={"name": var, "value": value})
        else:
            lines.append(f"{prefix}create variable {var}={value}")
            if apply:
                gh("-X", "POST", f"{base}/variables", body={"name": var, "value": value})
    return lines


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo", action="append", required=True, help="owner/name, repeatable")
    parser.add_argument("--apply", action="store_true", help="write; without it, a dry run")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args(argv)

    manifest = json.loads(args.manifest.read_text())
    refused = [r for r in args.repo if not manifest["repos"].get(r, {}).get("windows")]
    if refused:
        print(f"setup-windows-signing: not declared with \"windows\": true in {args.manifest.name}: "
              f"{', '.join(refused)}", file=sys.stderr)
        return 2
    for repo in args.repo:
        print(repo)
        for line in setup(repo, manifest, args.apply):
            print("  " + line)
    if not args.apply:
        print("dry run: nothing was changed; add --apply to write")
    else:
        print("next: setup-release-env.py --repo … --apply (account variables), then a rehearsal on a vX.Y.Z-rc.N tag "
              "with AZURE_SIGNING_ENABLED=true; role assignments can take a few minutes to reach the signing service")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except AzError as exc:
        print(exc.code, file=sys.stderr)
        sys.exit(1)
