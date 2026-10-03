"""actions/sign-sums/sign-sums.sh with a real gpg and a throwaway key.

Contract: SHA256SUMS lists every file of the folder (and not itself), SHA256SUMS.asc verifies
against the public key, a changed file no longer matches, the passphrase is never printed,
and nothing of the key stays on disk.
"""
from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "actions" / "sign-sums" / "sign-sums.sh"
PASSPHRASE = "test-passphrase-not-real-7f3a"


@unittest.skipUnless(shutil.which("gpg"), "gpg is not installed")
class SignSums(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keyhome = tempfile.mkdtemp(prefix="sk.", dir="/tmp")
        env = {**os.environ, "GNUPGHOME": cls.keyhome}
        subprocess.run(["gpg", "--batch", "--pinentry-mode", "loopback", "--passphrase", PASSPHRASE,
                        "--quick-generate-key", "Test release key <test@example.invalid>", "ed25519", "sign", "1d"],
                       env=env, check=True, capture_output=True)
        cls.private = subprocess.run(["gpg", "--batch", "--pinentry-mode", "loopback", "--passphrase", PASSPHRASE,
                                      "--armor", "--export-secret-keys"], env=env, check=True, capture_output=True).stdout
        cls.public = subprocess.run(["gpg", "--batch", "--armor", "--export"], env=env, check=True,
                                    capture_output=True).stdout
        subprocess.run(["gpgconf", "--kill", "gpg-agent"], env=env, capture_output=True)
        shutil.rmtree(cls.keyhome, ignore_errors=True)

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "app-1.0.zip").write_bytes(b"zip bytes")
        (self.dir / "app-1.0.whl").write_bytes(b"wheel bytes")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_script(self, **env):
        base = {"PATH": os.environ["PATH"], "RELEASE_GPG_PRIVATE_KEY_B64": base64.b64encode(self.private).decode(),
                "RELEASE_GPG_PASSPHRASE": PASSPHRASE}
        return subprocess.run(["bash", str(SCRIPT), str(self.dir)], env={**base, **env}, capture_output=True,
                              text=True, stdin=subprocess.DEVNULL)

    def verify(self) -> subprocess.CompletedProcess:
        home = tempfile.mkdtemp(prefix="sv.", dir="/tmp")
        try:
            env = {**os.environ, "GNUPGHOME": home}
            subprocess.run(["gpg", "--batch", "--import"], input=self.public, env=env, check=True, capture_output=True)
            return subprocess.run(["gpg", "--batch", "--verify", str(self.dir / "SHA256SUMS.asc"),
                                   str(self.dir / "SHA256SUMS")], env=env, capture_output=True)
        finally:
            subprocess.run(["gpgconf", "--kill", "gpg-agent"], env={**os.environ, "GNUPGHOME": home}, capture_output=True)
            shutil.rmtree(home, ignore_errors=True)

    def test_sums_every_file_and_the_signature_verifies(self):
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        sums = (self.dir / "SHA256SUMS").read_text().splitlines()
        self.assertEqual([line.split("  ")[1] for line in sums], ["app-1.0.whl", "app-1.0.zip"])
        self.assertEqual(self.verify().returncode, 0)
        self.assertIn("fingerprint=", r.stdout)
        check = subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS"], cwd=self.dir, capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stdout)

    def test_a_changed_file_no_longer_matches(self):
        self.run_script()
        (self.dir / "app-1.0.zip").write_bytes(b"tampered")
        check = subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS"], cwd=self.dir, capture_output=True)
        self.assertNotEqual(check.returncode, 0)

    def test_the_passphrase_is_never_printed_and_the_key_home_is_gone(self):
        before = set(Path("/tmp").glob("sums.*"))
        r = self.run_script()
        self.assertNotIn(PASSPHRASE, r.stdout + r.stderr)
        self.assertEqual(set(Path("/tmp").glob("sums.*")) - before, set())

    def test_a_missing_input_is_refused_by_name(self):
        r = self.run_script(RELEASE_GPG_PASSPHRASE="")
        self.assertEqual(r.returncode, 2)
        self.assertIn("RELEASE_GPG_PASSPHRASE", r.stderr)
        self.assertFalse((self.dir / "SHA256SUMS").exists())


if __name__ == "__main__":
    unittest.main()
