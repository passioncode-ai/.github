"""actions/notarize/notarize.sh with Apple's tools faked on PATH.

Contract: an .app is zipped, submitted, stapled, validated and assessed as an executable; a
.dmg is submitted, stapled and assessed with the primary-signature context; a .pkg is assessed
as an installer. Anything not Accepted prints Apple's log and fails without stapling. The API
key reaches notarytool as a file in a private temp directory that is gone afterwards, and
none of the credentials is printed.
"""
from __future__ import annotations

import base64
import json
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "actions" / "notarize" / "notarize.sh"
KEY_ID, ISSUER = "FAKEKEY123", "00000000-0000-4000-8000-0000000000aa"
KEY_B64 = base64.b64encode(b"placeholder key body, never parsed by the script\n").decode()

FAKES = {
    "xcrun": textwrap.dedent("""\
        echo "xcrun $*" >> "$FAKE_DIR/calls"
        if [[ "$1 $2" == "notarytool submit" ]]; then
          # Record whether the key file exists while notarytool runs, and its mode.
          prev=""; for a in "$@"; do [[ "$prev" == --key ]] && python3 -c 'import os,sys; print(format(os.stat(sys.argv[1]).st_mode & 0o777, "o"))' "$a" > "$FAKE_DIR/keymode"; [[ "$prev" == --key ]] && echo "$a" > "$FAKE_DIR/keypath"; prev=$a; done
          cat "$FAKE_DIR/submit.json"
        elif [[ "$1 $2" == "notarytool log" ]]; then echo '{"issues":[{"message":"The signature of the binary is invalid."}]}'
        elif [[ "$1" == stapler ]]; then echo "The $2 action worked!"; fi"""),
    "spctl": 'echo "spctl $*" >> "$FAKE_DIR/calls"; echo accepted >&2',
    "ditto": 'echo "ditto $*" >> "$FAKE_DIR/calls"; : > "${@: -1}"',
    "codesign": 'echo "codesign $*" >> "$FAKE_DIR/calls"; printf "Authority=Developer ID Application: Example (EXAMPLE123)\\nCodeDirectory v=1 flags=0x10000(runtime)\\n" >&2',
}


class Notarize(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        for name, body in FAKES.items():
            p = bin_dir / name
            p.write_text("#!/bin/bash\n" + body + "\n")
            p.chmod(p.stat().st_mode | stat.S_IXUSR)
        (bin_dir / "python3").symlink_to(sys.executable)
        self.path = f"{bin_dir}:/usr/bin:/bin"

    def tearDown(self):
        self._tmp.cleanup()

    def run_on(self, target: Path, status: str = "Accepted", **env):
        (self.tmp / "submit.json").write_text(json.dumps(
            {"id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee", "status": status, "message": "Processing complete"}))
        base = {"PATH": self.path, "FAKE_DIR": str(self.tmp), "RUNNER_TEMP": str(self.tmp),
                "ASC_KEY_ID": KEY_ID, "ASC_ISSUER_ID": ISSUER, "ASC_API_KEY_P8_B64": KEY_B64}
        return subprocess.run(["bash", str(SCRIPT), str(target)], env={**base, **env}, capture_output=True, text=True)

    def calls(self):
        f = self.tmp / "calls"
        return f.read_text().splitlines() if f.exists() else []

    def make(self, name: str) -> Path:
        p = self.tmp / name
        if name.endswith(".app"):
            (p / "Contents").mkdir(parents=True)
        else:
            p.write_bytes(b"x")
        return p

    def test_an_app_is_zipped_submitted_stapled_and_assessed(self):
        app = self.make("Example.app")
        r = self.run_on(app)
        self.assertEqual(r.returncode, 0, r.stderr)
        c = self.calls()
        self.assertTrue(c[0].startswith("ditto -c -k --keepParent"))
        self.assertIn(f"xcrun stapler staple {app}", c)
        self.assertIn(f"xcrun stapler validate {app}", c)
        self.assertTrue(any(x.startswith("spctl --assess --type execute") and x.endswith(str(app)) for x in c))

    def test_a_dmg_is_assessed_by_its_primary_signature(self):
        dmg = self.make("Example.dmg")
        r = self.run_on(dmg)
        self.assertEqual(r.returncode, 0, r.stderr)
        c = self.calls()
        self.assertTrue(any(x.startswith(f"xcrun notarytool submit {dmg}") for x in c))
        self.assertIn(f"xcrun stapler staple {dmg}", c)
        self.assertTrue(any("--type open" in x and "context:primary-signature" in x for x in c))

    def test_a_pkg_is_assessed_as_an_installer(self):
        pkg = self.make("Example.pkg")
        r = self.run_on(pkg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(any(x.startswith("spctl --assess --type install") for x in self.calls()))

    def test_another_type_is_refused_before_upload(self):
        r = self.run_on(self.make("Example.tar.gz"))
        self.assertEqual(r.returncode, 2)
        self.assertFalse(any(x.startswith("xcrun") for x in self.calls()))

    def test_missing_credentials_are_refused_by_name(self):
        r = self.run_on(self.make("Example.dmg"), ASC_ISSUER_ID="")
        self.assertEqual(r.returncode, 2)
        self.assertIn("ASC_ISSUER_ID", r.stderr)
        self.assertFalse(any(x.startswith("xcrun") for x in self.calls()))

    def test_rejected_prints_apples_log_and_staples_nothing(self):
        r = self.run_on(self.make("Example.dmg"), status="Invalid")
        self.assertEqual(r.returncode, 1)
        self.assertIn("The signature of the binary is invalid.", r.stderr)
        self.assertFalse(any(x.startswith("xcrun stapler") for x in self.calls()))

    def test_the_key_is_a_private_temporary_file_and_nothing_secret_is_printed(self):
        r = self.run_on(self.make("Example.dmg"))
        self.assertEqual((self.tmp / "keymode").read_text().strip(), "600")
        self.assertFalse(Path((self.tmp / "keypath").read_text().strip()).exists())
        for secret in (KEY_ID, ISSUER, KEY_B64):
            self.assertNotIn(secret, r.stdout + r.stderr)

    def test_outputs_name_the_submission(self):
        r = self.run_on(self.make("Example.dmg"))
        self.assertIn("submission=aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee", r.stdout)


if __name__ == "__main__":
    unittest.main()
