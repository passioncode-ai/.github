#!/usr/bin/env python3
"""Copy release credentials from this process's environment into the products' `release`
environments on GitHub, over stdin, without printing a value.

Run it under a runner that injects the values from the vault, one slot at a time:

    python3 "$(project-observatory full-path)/tools/use_secret.py" run --env prod \\
      passioncode-release APPLE_DEVELOPER_ID_P12_B64,APPLE_DEVELOPER_ID_P12_PASSWORD,... -- \\
      scripts/sync-release-secrets.py --all --apply

For each repository, the secret names are the union of its groups in
release-signing/products.json. A name present in this environment is set with
`gh secret set NAME --env release --repo R`, its value on stdin (never argv). A name absent
here is reported as `absent`, because another slot's run sets it; --strict makes absence an
error. An empty value is never sent. Output: name, then the first 12 hex digits of the value's
sha256, so two runs can be compared without seeing the secret. A dry run is the default.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "release-signing" / "products.json"


def names_for(manifest: dict, repo: str) -> list[str]:
    out: list[str] = []
    for group in manifest["repos"][repo]["groups"]:
        out += [n for n in manifest["groups"][group] if n not in out]
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--repo", action="append", help="owner/name, repeatable")
    target.add_argument("--all", action="store_true", help="every repository in the manifest")
    parser.add_argument("--apply", action="store_true", help="write; without it, a dry run")
    parser.add_argument("--strict", action="store_true", help="fail when a listed name is absent here")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args(argv)

    manifest = json.loads(args.manifest.read_text())
    repos = list(manifest["repos"]) if args.all else args.repo
    unknown = [r for r in repos if r not in manifest["repos"]]
    if unknown:
        print(f"sync-release-secrets: not in {args.manifest.name}: {', '.join(unknown)}", file=sys.stderr)
        return 2

    absent_any = failed = False
    for repo in repos:
        print(repo)
        for name in names_for(manifest, repo):
            value = os.environ.get(name)
            if value is None:
                absent_any = True
                print(f"  {name}: absent here (set by another slot's run)")
                continue
            if value == "":
                print(f"  {name}: empty here, not sent")
                continue
            fingerprint = hashlib.sha256(value.encode()).hexdigest()[:12]
            if not args.apply:
                print(f"  would set {name} (sha256 {fingerprint})")
                continue
            proc = subprocess.run(["gh", "secret", "set", name, "--env", manifest["environment"], "--repo", repo],
                                  input=value, capture_output=True, text=True)
            if proc.returncode == 0:
                print(f"  set {name} (sha256 {fingerprint})")
            else:
                failed = True
                # gh's message names the repository or the permission; it never echoes the body.
                print(f"  {name}: FAILED: {proc.stderr.strip()[:200]}")
    if not args.apply:
        print("dry run: nothing was sent; add --apply to write")
    if failed:
        return 1
    if args.strict and absent_any:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
