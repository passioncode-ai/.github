"""Windows signing: the shared actions, the manifest's `azure` block and setup-windows-signing.py.

The contract: every product that ships for Windows signs through one Azure Artifact Signing
account and profile, each with its own OIDC identity bound to its own `release` environment;
the setup script is a dry run unless told otherwise, creates only what is missing, and grants
nothing broader than the signer role on that one account.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import fakeaz  # noqa: E402
import fakegh  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SETUP_WIN = ROOT / "scripts" / "setup-windows-signing.py"
SETUP_ENV = ROOT / "scripts" / "setup-release-env.py"
MANIFEST = ROOT / "release-signing" / "products.json"
ACCOUNT_ID = "/subscriptions/sub-1/resourceGroups/rg-passioncode-signing/providers/Microsoft.CodeSigning/codeSigningAccounts/passioncodesigning"


def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def windows_repos() -> list[str]:
    return [r for r, c in manifest()["repos"].items() if c.get("windows")]


def run(script: Path, args: list[str], env: dict[str, str]):
    return subprocess.run([sys.executable, str(script), *args], env=env, capture_output=True, text=True)


def gh_writes(tmp: Path) -> list[dict]:
    return [c for c in fakegh.calls(tmp) if c["argv"][:1] == ["api"] and "-X" in c["argv"]
            and c["argv"][c["argv"].index("-X") + 1] in {"PUT", "POST", "PATCH", "DELETE"}]


class Manifest(unittest.TestCase):
    def test_the_shared_account_is_named_once(self):
        azure = manifest()["azure_signing"]
        for key in ("resource_group", "account", "endpoint", "certificate_profile", "role", "app_prefix"):
            self.assertTrue(azure.get(key), key)
        self.assertTrue(azure["endpoint"].startswith("https://") and azure["endpoint"].endswith(".codesigning.azure.net/"))

    def test_no_tenant_or_subscription_in_the_public_manifest(self):
        # They are read from the operator's `az` session at setup time, not published here.
        text = MANIFEST.read_text()
        self.assertNotRegex(text, r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

    def test_every_windows_product_says_whether_signing_is_on(self):
        self.assertIn("passioncode-ai/fabric-switchboard", windows_repos())
        for repo in windows_repos():
            value = manifest()["repos"][repo].get("vars", {}).get("AZURE_SIGNING_ENABLED")
            self.assertIn(value, ("true", "false"), repo)

    def test_switchboard_signs(self):
        # Switched on 2026-10-10 in its release environment; the manifest said "false" and a
        # setup-release-env run would have switched it off again.
        self.assertEqual(manifest()["repos"]["passioncode-ai/fabric-switchboard"]["vars"]["AZURE_SIGNING_ENABLED"], "true")


class SetupReleaseEnvAzure(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def created_variables(self, repo: str) -> dict[str, str]:
        env = fakegh.install(self.tmp, {"team_id": 42})
        result = run(SETUP_ENV, ["--repo", repo, "--apply"], env)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = {}
        for c in gh_writes(self.tmp):
            if any(a.endswith("/variables") for a in c["argv"]):
                body = json.loads(c["stdin"])
                out[body["name"]] = body["value"]
        return out

    def test_a_windows_product_gets_the_shared_account(self):
        azure = manifest()["azure_signing"]
        got = self.created_variables("passioncode-ai/fabric-switchboard")
        self.assertEqual(got["AZURE_SIGNING_ENDPOINT"], azure["endpoint"])
        self.assertEqual(got["AZURE_SIGNING_ACCOUNT"], azure["account"])
        self.assertEqual(got["AZURE_CERTIFICATE_PROFILE"], azure["certificate_profile"])
        self.assertEqual(got["AZURE_SIGNING_ENABLED"], "true")

    def test_a_product_without_windows_gets_none(self):
        repo = next(r for r, c in manifest()["repos"].items() if not c.get("windows"))
        got = self.created_variables(repo)
        self.assertFalse([n for n in got if n.startswith("AZURE_")], got)


class SetupWindowsSigning(unittest.TestCase):
    REPO = "passioncode-ai/fabric-switchboard"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.az_state = {"tenant": "tenant-1", "subscription": "sub-1",
                         "accounts": {"passioncodesigning": ACCOUNT_ID}}

    def tearDown(self):
        self._tmp.cleanup()

    def env(self, gh_state: dict | None = None) -> dict[str, str]:
        env = fakegh.install(self.tmp, gh_state or {"team_id": 42})
        env.update(fakeaz.install(self.tmp, self.az_state))
        return env

    def test_dry_run_creates_nothing_and_names_each_step(self):
        result = run(SETUP_WIN, ["--repo", self.REPO], self.env())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(fakeaz.creates(self.tmp), [])
        self.assertEqual(gh_writes(self.tmp), [])
        for words in ("would create app registration github-release-signing-fabric-switchboard",
                      "would add federated credential repo:passioncode-ai/fabric-switchboard:environment:release",
                      "would assign", "would create variable AZURE_CLIENT_ID"):
            self.assertIn(words, result.stdout)

    def test_apply_creates_one_identity_bound_to_the_release_environment(self):
        result = run(SETUP_WIN, ["--repo", self.REPO, "--apply"], self.env())
        self.assertEqual(result.returncode, 0, result.stderr)
        s = fakeaz.state(self.tmp)
        [app] = s["apps"]
        self.assertEqual(app["displayName"], "github-release-signing-fabric-switchboard")
        [fic] = app["fic"]
        self.assertEqual(fic["subject"], "repo:passioncode-ai/fabric-switchboard:environment:release")
        self.assertEqual(fic["issuer"], "https://token.actions.githubusercontent.com")
        self.assertEqual(fic["audiences"], ["api://AzureADTokenExchange"])
        [role] = s["roles"]
        self.assertEqual(role["scope"], ACCOUNT_ID)
        self.assertEqual(role["roleDefinitionName"], manifest()["azure_signing"]["role"])
        self.assertEqual(role["principalType"], "ServicePrincipal")
        self.assertEqual(role["principalId"], s["sps"][app["appId"]]["id"])
        variables = {json.loads(c["stdin"])["name"]: json.loads(c["stdin"])["value"] for c in gh_writes(self.tmp)}
        self.assertEqual(variables, {"AZURE_CLIENT_ID": app["appId"], "AZURE_TENANT_ID": "tenant-1",
                                     "AZURE_SUBSCRIPTION_ID": "sub-1"})

    def test_a_second_run_changes_nothing(self):
        run(SETUP_WIN, ["--repo", self.REPO, "--apply"], self.env())
        app = fakeaz.state(self.tmp)["apps"][0]
        self.az_state = fakeaz.state(self.tmp)
        (self.tmp / "az-calls.jsonl").unlink()
        (self.tmp / "calls.jsonl").unlink()
        gh_state = {"team_id": 42, "variables": [{"name": "AZURE_CLIENT_ID", "value": app["appId"]},
                                                 {"name": "AZURE_TENANT_ID", "value": "tenant-1"},
                                                 {"name": "AZURE_SUBSCRIPTION_ID", "value": "sub-1"}]}
        result = run(SETUP_WIN, ["--repo", self.REPO, "--apply"], self.env(gh_state))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(fakeaz.creates(self.tmp), [])
        self.assertEqual(gh_writes(self.tmp), [])
        self.assertIn("unchanged", result.stdout)

    def test_an_identity_the_environment_already_names_is_kept(self):
        # Fabric Inbox's and Switchboard's identities were made by hand before this script.
        self.az_state["apps"] = [{"appId": "11111111-aaaa", "id": "obj-x", "displayName": "made-by-hand", "fic": []}]
        gh_state = {"team_id": 42, "variables": [{"name": "AZURE_CLIENT_ID", "value": "11111111-aaaa"}]}
        result = run(SETUP_WIN, ["--repo", self.REPO, "--apply"], self.env(gh_state))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse([a for a in fakeaz.creates(self.tmp) if a[:3] == ["ad", "app", "create"]])
        self.assertEqual(len(fakeaz.state(self.tmp)["apps"]), 1)
        self.assertIn("made-by-hand", result.stdout)

    def test_a_repository_not_declared_for_windows_is_refused(self):
        repo = next(r for r, c in manifest()["repos"].items() if not c.get("windows"))
        result = run(SETUP_WIN, ["--repo", repo, "--apply"], self.env())
        self.assertEqual(result.returncode, 2)
        self.assertIn("windows", result.stderr)
        self.assertEqual(fakeaz.creates(self.tmp), [])

    def test_an_expired_az_session_is_named_not_retried(self):
        self.az_state["expired"] = True
        result = run(SETUP_WIN, ["--repo", self.REPO, "--apply"], self.env())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("az login", result.stderr)
        self.assertEqual(len(fakeaz.calls(self.tmp)), 1)


class Actions(unittest.TestCase):
    def manifests(self):
        return sorted(ROOT.glob("actions/windows-signing/**/action.yml")) + [ROOT / "actions/windows-signing/action.yml"]

    def test_third_party_actions_are_pinned_by_commit(self):
        for path in ROOT.glob("actions/**/action.yml"):
            for line in path.read_text().splitlines():
                m = re.search(r"uses:\s*([^\s#]+)", line)
                if m and not m.group(1).startswith(("./", "passioncode-ai/")):
                    self.assertRegex(m.group(1), r"@[0-9a-f]{40}$", f"{path.relative_to(ROOT)}: {line.strip()}")

    def test_the_signer_uses_only_the_jobs_oidc_sign_in(self):
        text = (ROOT / "actions/windows-signing/action.yml").read_text()
        excluded = re.findall(r"exclude-([a-z-]+)-credential: (true|false)", text)
        self.assertEqual({k for k, v in excluded if v == "false"}, {"azure-cli"})
        self.assertGreaterEqual(len(excluded), 10)
        self.assertIn("timestamp-rfc3161: http://timestamp.acs.microsoft.com", text)
        self.assertIn("file-digest: SHA256", text)

    def test_signing_is_always_followed_by_the_verification(self):
        text = (ROOT / "actions/windows-signing/action.yml").read_text()
        self.assertLess(text.index("artifact-signing-action"), text.index("verify/verify.ps1"))

    def test_the_verification_requires_a_timestamp(self):
        text = (ROOT / "actions/windows-signing/verify/verify.ps1").read_text()
        self.assertIn("TimeStamperCertificate", text)
        self.assertIn("'Valid'", text)


if __name__ == "__main__":
    unittest.main()
