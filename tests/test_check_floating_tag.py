"""scripts/check-floating-tag.py against a real throwaway Git repository: `v1` on the newest
`v1.X.Y` passes; `v1` left on an older release (the ORGPROFILE-06 lag), a missing `v1`, no
release at all and an unreadable remote fail; annotated and lightweight tags are compared by
commit; pre-releases and other majors are ignored."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-floating-tag.py"
ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
       "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}


class FloatingTag(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.git("init", "-q")
        self.commits = [self.commit(str(i)) for i in range(3)]

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.repo), *args], env=ENV, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, message: str) -> str:
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def tag(self, name: str, commit: str, annotated: bool = True) -> None:
        self.git("tag", *(["-a", "-m", name] if annotated else []), name, commit)

    def check(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), "--remote", str(self.repo), *extra],
                              env=ENV, capture_output=True, text=True, timeout=60)

    def test_v1_on_the_newest_release_passes(self):
        self.tag("v1.3.1", self.commits[0])
        self.tag("v1.4.0", self.commits[2])
        self.tag("v1", self.commits[2], annotated=False)
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("v1 = v1.4.0", result.stdout)

    def test_v1_left_on_an_older_release_fails_and_names_both(self):
        self.tag("v1.3.1", self.commits[0])
        self.tag("v1.3.2", self.commits[1])
        self.tag("v1.4.0", self.commits[2])
        self.tag("v1", self.commits[0])
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("NOT IN STEP", result.stdout)
        self.assertIn("(v1.3.1)", result.stdout)
        self.assertIn("newest release v1.4.0", result.stdout)

    def test_releases_compare_as_numbers_not_text(self):
        self.tag("v1.9.0", self.commits[0])
        self.tag("v1.10.0", self.commits[1])
        self.tag("v1", self.commits[0])
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("newest release v1.10.0", result.stdout)

    def test_pre_releases_and_other_majors_are_ignored(self):
        self.tag("v1.4.0", self.commits[0])
        self.tag("v1.5.0-rc.1", self.commits[1])
        self.tag("v2.0.0", self.commits[2])
        self.tag("v1", self.commits[0])
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_missing_floating_tag_fails(self):
        self.tag("v1.4.0", self.commits[0])
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("v1 is missing", result.stdout)

    def test_no_release_fails(self):
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("no v1.X.Y release", result.stdout)

    def test_an_unreadable_remote_is_never_in_step(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--remote", str(self.repo / "absent")],
                                env=ENV, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertNotIn("in step", result.stdout)


if __name__ == "__main__":
    unittest.main()
