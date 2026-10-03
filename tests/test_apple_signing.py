"""actions/apple-signing/setup.sh with `security` faked on PATH.

Contract: it outputs the Developer ID identity of the team; with the MAS .p12s it finds the
application and installer identities under either of Apple's names (the fallback name must be
reached — a silent exit before it was a real defect, 2026-10-03); a missing identity is an
explicit error; no input value is printed.
"""
from __future__ import annotations

import base64
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "actions" / "apple-signing" / "setup.sh"
TEAM = "EXAMPLE123"
H = "0123456789ABCDEF0123456789ABCDEF01234567"

FAKE_SECURITY = textwrap.dedent('''\
    #!/bin/bash
    echo "security $*" >> "$FAKE_DIR/calls"
    case "$1" in
      find-identity)
        policy=codesigning; prev=""; for a in "$@"; do [[ "$prev" == -p ]] && policy=$a; prev=$a; done
        cat "$FAKE_DIR/identities.$policy" 2>/dev/null; echo "     N valid identities found" ;;
      list-keychains) echo '    "/home/x/login.keychain-db"' ;;
    esac
    exit 0
    ''')


class AppleSigningSetup(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        b = self.tmp / "bin"
        b.mkdir()
        s = b / "security"
        s.write_text(FAKE_SECURITY)
        s.chmod(s.stat().st_mode | stat.S_IXUSR)
        self.path = f"{b}:/usr/bin:/bin"

    def tearDown(self):
        self._tmp.cleanup()

    def identities(self, codesigning: list[str], basic: list[str] | None = None):
        fmt = lambda names: "".join(f'  {i + 1}) {H} "{n}"\n' for i, n in enumerate(names))
        (self.tmp / "identities.codesigning").write_text(fmt(codesigning))
        (self.tmp / "identities.basic").write_text(fmt(basic if basic is not None else codesigning))

    def run_setup(self, mas: bool = False):
        p12 = base64.b64encode(b"not a real p12").decode()
        env = {"PATH": self.path, "FAKE_DIR": str(self.tmp), "TEAM_ID": TEAM, "KEYCHAIN": str(self.tmp / "k.keychain-db"),
               "DEVELOPER_ID_P12_B64": p12, "P12_PASSWORD": "pw-not-real-1"}
        if mas:
            env.update(DISTRIBUTION_P12_B64=p12, INSTALLER_P12_B64=p12, MAS_P12_PASSWORD="pw-not-real-2")
        return subprocess.run(["bash", str(SETUP)], env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)

    def test_the_developer_id_of_the_team_is_output(self):
        self.identities([f"Developer ID Application: Someone Else (OTHERTEAM1)", f"Developer ID Application: Example ({TEAM})"])
        r = self.run_setup()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"identity=Developer ID Application: Example ({TEAM})", r.stdout)

    def test_mas_identities_are_found_under_the_fallback_names(self):
        app = f"3rd Party Mac Developer Application: Example ({TEAM})"
        inst = f"3rd Party Mac Developer Installer: Example ({TEAM})"
        self.identities([f"Developer ID Application: Example ({TEAM})", app],
                        [f"Developer ID Application: Example ({TEAM})", app, inst])
        r = self.run_setup(mas=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"mas_app_identity={app}", r.stdout)
        self.assertIn(f"mas_installer_identity={inst}", r.stdout)

    def test_a_missing_developer_id_is_an_explicit_error(self):
        self.identities([f"Apple Development: Example ({TEAM})"])
        r = self.run_setup()
        self.assertEqual(r.returncode, 1)
        self.assertIn("no valid 'Developer ID Application' identity", r.stderr)

    def test_a_missing_mas_installer_is_an_explicit_error(self):
        self.identities([f"Developer ID Application: Example ({TEAM})", f"3rd Party Mac Developer Application: Example ({TEAM})"])
        r = self.run_setup(mas=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no Mac installer identity", r.stderr)

    def test_passwords_never_reach_the_output_or_argv_logged(self):
        self.identities([f"Developer ID Application: Example ({TEAM})"])
        r = self.run_setup()
        self.assertNotIn("pw-not-real-1", r.stdout + r.stderr)
        # security import takes the .p12 password with -P (Apple's tool has no stdin form); the
        # keychain password is random. Both live only in the job's process table on an ephemeral
        # runner — recorded here so a change to that is a visible decision.
        calls = (self.tmp / "calls").read_text()
        self.assertIn("import", calls)


if __name__ == "__main__":
    unittest.main()
