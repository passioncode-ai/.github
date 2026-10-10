"""setup-release-env.py and sync-release-secrets.py against a fake `gh`.

The contract: a dry run changes nothing; --apply makes the environment exactly as the design
says (team reviewers, no self-review, no admin bypass, only `v*` tags) and is idempotent; a
secret value travels on stdin only and is never printed.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import fakegh  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "scripts" / "setup-release-env.py"
SYNC = ROOT / "scripts" / "sync-release-secrets.py"
MANIFEST = ROOT / "release-signing" / "products.json"
REPO = "passioncode-ai/fabric-dashboards"


def run(script: Path, args: list[str], env: dict[str, str], extra: dict[str, str] | None = None):
    return subprocess.run([sys.executable, str(script), *args], env={**env, **(extra or {})},
                          capture_output=True, text=True)


def mutating(calls: list[dict]) -> list[dict]:
    out = []
    for c in calls:
        a = c["argv"]
        if a[:2] == ["secret", "set"]:
            out.append(c)
        elif a[:1] == ["api"] and "-X" in a and a[a.index("-X") + 1] in {"PUT", "POST", "PATCH", "DELETE"}:
            out.append(c)
    return out


class SetupReleaseEnv(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_dry_run_changes_nothing_and_says_what_it_would_do(self):
        env = fakegh.install(self.tmp, {"team_id": 42})
        result = run(SETUP, ["--repo", REPO], env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(mutating(fakegh.calls(self.tmp)), [])
        self.assertIn("would", result.stdout)
        self.assertIn("v*", result.stdout)

    def test_apply_makes_the_environment_the_design_names(self):
        env = fakegh.install(self.tmp, {"team_id": 42})
        result = run(SETUP, ["--repo", REPO, "--apply"], env)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = mutating(fakegh.calls(self.tmp))
        put = next(c for c in calls if f"repos/{REPO}/environments/release" in c["argv"] and "PUT" in c["argv"])
        body = json.loads(put["stdin"])
        self.assertEqual(body["reviewers"], [{"type": "Team", "id": 42}])
        manifest = json.loads(MANIFEST.read_text())
        self.assertIs(body["prevent_self_review"], manifest["prevent_self_review"])
        self.assertIs(body["can_admins_bypass"], False)
        self.assertEqual(body["deployment_branch_policy"], {"protected_branches": False, "custom_branch_policies": True})
        policy = next(c for c in calls if any(a.endswith("/deployment-branch-policies") for a in c["argv"]))
        self.assertEqual(json.loads(policy["stdin"]), {"name": "v*", "type": "tag"})
        access = next(c for c in calls if any(a.endswith(f"teams/release-approvers/repos/{REPO}") for a in c["argv"]))
        self.assertEqual(json.loads(access["stdin"]), {"permission": "pull"})
        # The team gets access before the environment names it as a reviewer.
        self.assertLess(calls.index(access), calls.index(put))
        variable = next(c for c in calls if any("/variables" in a for a in c["argv"]))
        self.assertEqual(json.loads(variable["stdin"]), {"name": "APPLE_TEAM_ID", "value": "KJ35UYYL22"})

    def test_the_manifest_can_restore_four_eyes(self):
        manifest = json.loads(MANIFEST.read_text())
        manifest["prevent_self_review"] = True
        alt = self.tmp / "products.json"
        alt.write_text(json.dumps(manifest))
        env = fakegh.install(self.tmp, {"team_id": 42})
        result = run(SETUP, ["--repo", REPO, "--apply", "--manifest", str(alt)], env)
        self.assertEqual(result.returncode, 0, result.stderr)
        put = next(c for c in mutating(fakegh.calls(self.tmp)) if "PUT" in c["argv"] and c["argv"][-3].endswith("/environments/release"))
        self.assertIs(json.loads(put["stdin"])["prevent_self_review"], True)

    def test_apply_is_idempotent(self):
        env = fakegh.install(self.tmp, {
            "team_id": 42, "team_repos": [REPO],
            "env": {"name": "release", "can_admins_bypass": False,
                    "protection_rules": [{"type": "required_reviewers", "prevent_self_review": json.loads(MANIFEST.read_text())["prevent_self_review"],
                                          "reviewers": [{"type": "Team", "reviewer": {"id": 42}}]}],
                    "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True}},
            "policies": [{"name": "v*", "type": "tag"}],
            "variables": [{"name": "APPLE_TEAM_ID", "value": "KJ35UYYL22"},
                          # Dashboards ships for Windows: the shared Artifact Signing account's too.
                          {"name": "AZURE_SIGNING_ENABLED", "value": json.loads(MANIFEST.read_text())["repos"][REPO]["vars"]["AZURE_SIGNING_ENABLED"]},
                          {"name": "AZURE_SIGNING_ENDPOINT", "value": "https://neu.codesigning.azure.net/"},
                          {"name": "AZURE_SIGNING_ACCOUNT", "value": "passioncodesigning"},
                          {"name": "AZURE_CERTIFICATE_PROFILE", "value": "passioncode-public-trust"}]})
        result = run(SETUP, ["--repo", REPO, "--apply"], env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(mutating(fakegh.calls(self.tmp)), [], result.stdout)
        self.assertIn("unchanged", result.stdout)

    def test_a_repository_outside_the_manifest_is_refused(self):
        env = fakegh.install(self.tmp, {"team_id": 42})
        result = run(SETUP, ["--repo", "passioncode-ai/not-a-product", "--apply"], env)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(mutating(fakegh.calls(self.tmp)), [])


SECRET_VALUES = {"ASC_KEY_ID": "KEYID-not-real-1", "ASC_ISSUER_ID": "issuer-not-real-2",
                 "ASC_API_KEY_P8_B64": "cDgtbm90LXJlYWwtMw==", "RELEASE_GPG_PASSPHRASE": "gpg-not-real-4",
                 "ANDROID_KEY_PASSWORD": "android-not-real-5"}


class SyncReleaseSecrets(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.env = fakegh.install(self.tmp, {})

    def tearDown(self):
        self._tmp.cleanup()

    def test_dry_run_sets_nothing_and_prints_no_value(self):
        result = run(SYNC, ["--repo", REPO], self.env, SECRET_VALUES)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(mutating(fakegh.calls(self.tmp)), [])
        self.assertIn("ASC_KEY_ID", result.stdout)
        for value in SECRET_VALUES.values():
            self.assertNotIn(value, result.stdout + result.stderr)

    def test_apply_sends_each_value_on_stdin_only(self):
        result = run(SYNC, ["--repo", REPO, "--apply"], self.env, SECRET_VALUES)
        self.assertEqual(result.returncode, 0, result.stderr)
        sets = mutating(fakegh.calls(self.tmp))
        by_name = {c["argv"][2]: c for c in sets}
        # The repository's manifest groups (apple, gpg) decide the names; ANDROID_* is not set here.
        self.assertEqual(sorted(by_name), ["ASC_API_KEY_P8_B64", "ASC_ISSUER_ID", "ASC_KEY_ID", "RELEASE_GPG_PASSPHRASE"])
        for name, call in by_name.items():
            self.assertEqual(call["argv"], ["secret", "set", name, "--env", "release", "--repo", REPO])
            self.assertEqual(call["stdin"], SECRET_VALUES[name])
        for value in SECRET_VALUES.values():
            self.assertNotIn(value, result.stdout + result.stderr)

    def test_listed_names_absent_from_the_environment_are_reported(self):
        result = run(SYNC, ["--repo", REPO, "--apply"], self.env, SECRET_VALUES)
        self.assertIn("absent", result.stdout)
        self.assertIn("APPLE_DEVELOPER_ID_P12_B64", result.stdout)
        strict = run(SYNC, ["--repo", REPO, "--apply", "--strict"], self.env, SECRET_VALUES)
        self.assertEqual(strict.returncode, 2)

    def test_an_empty_value_is_never_sent(self):
        result = run(SYNC, ["--repo", REPO, "--apply"], self.env, {**SECRET_VALUES, "ASC_KEY_ID": ""})
        names = [c["argv"][2] for c in mutating(fakegh.calls(self.tmp))]
        self.assertNotIn("ASC_KEY_ID", names)
        self.assertIn("empty", result.stdout)


if __name__ == "__main__":
    unittest.main()
