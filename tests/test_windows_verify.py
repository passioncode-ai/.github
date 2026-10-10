"""actions/windows-signing/verify/verify.ps1 against real files, on Windows.

Runs where PowerShell 7 and Authenticode exist (the self-test's `windows` job): the running
pwsh.exe is Microsoft-signed with a timestamp and must pass; an unsigned copy of a script must
fail and be named; a signer that is not the expected one must fail.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "actions" / "windows-signing" / "verify" / "verify.ps1"
PWSH = shutil.which("pwsh")


@unittest.skipUnless(os.name == "nt" and PWSH, "needs Windows and PowerShell 7")
class Verify(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.out = self.tmp / "report" / "signatures.json"

    def tearDown(self):
        self._tmp.cleanup()

    def verify(self, files: str, expected: str = ""):
        return subprocess.run([PWSH, "-NoProfile", "-File", str(VERIFY), "-Files", files, "-Out", str(self.out),
                               "-ExpectedSubject", expected], capture_output=True, text=True)

    def test_a_signed_timestamped_file_passes_and_is_reported(self):
        result = self.verify(PWSH, "Microsoft")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        [row] = json.loads(self.out.read_text(encoding="utf-8-sig"))
        self.assertEqual(row["status"], "Valid")
        self.assertIn("Microsoft", row["signer"])
        self.assertTrue(row["timestamper"])
        self.assertEqual(len(row["sha256"]), 64)

    def test_an_unsigned_file_fails_and_is_named(self):
        unsigned = self.tmp / "unsigned.ps1"
        unsigned.write_text("Write-Host hi\n")
        result = self.verify(f"{PWSH}\n{unsigned}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsigned.ps1", result.stdout + result.stderr)
        self.assertFalse(self.out.exists())

    def test_another_signer_fails(self):
        result = self.verify(PWSH, "O=Siarhei Sheleh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not by", result.stdout + result.stderr)

    def test_a_pattern_matching_nothing_fails(self):
        result = self.verify(str(self.tmp / "missing-*.exe"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no file matches", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
