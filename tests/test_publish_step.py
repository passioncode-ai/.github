"""The `Create the release` step of release-publish.yml, run with a fake `gh`.

Contract: a new tag becomes a draft and is then published; -alpha/-beta/-preview tags are marked
prerelease under `auto`; an -rc tag is refused (rehearsals never publish); a published
release is never rewritten; a draft is completed; a release that is not newer than the latest
one is refused before anything is written (an old run approved late would otherwise become
"latest", and every installed copy reads its update feed from releases/latest), unless
`allow-older` publishes it without making it latest.
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release-publish.yml"


def step_script() -> str:
    text = WORKFLOW.read_text()
    start = text.index("- name: Create the release")
    block = text[start:]
    run = block.index("        run: |\n") + len("        run: |\n")
    lines = []
    for line in block[run:].splitlines():
        if line and not line.startswith("          "):
            break
        lines.append(line[10:])
    return "\n".join(lines) + "\n"


FAKE_GH = textwrap.dedent('''\
    #!/bin/bash
    echo "gh $*" >> "$FAKE_DIR/calls"
    if [[ "$1 $2" == "release view" ]]; then
      case "$(cat "$FAKE_DIR/state")" in
        absent) exit 1 ;;
        draft) [[ "$*" == *isDraft* ]] && echo true; [[ "$*" == *url* ]] && echo https://example.invalid/r; exit 0 ;;
        published) [[ "$*" == *isDraft* ]] && echo false; exit 0 ;;
      esac
    fi
    if [[ "$1 $2" == "release list" ]]; then
      [[ -f "$FAKE_DIR/latest" ]] && cat "$FAKE_DIR/latest"
      exit 0
    fi
    [[ "$*" == *"--json url"* ]] && echo https://example.invalid/r
    exit 0
    ''')


class PublishStep(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        (self.tmp / "bin").mkdir()
        gh = self.tmp / "bin" / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        (self.tmp / "dist").mkdir()
        (self.tmp / "dist" / "a.zip").write_bytes(b"x")
        (self.tmp / "notes.md").write_text("notes")
        (self.tmp / "step.sh").write_text(step_script())

    def tearDown(self):
        self._tmp.cleanup()

    def run_step(self, tag: str, state: str = "absent", prerelease: str = "auto", latest: str = "", allow_older: str = "false"):
        (self.tmp / "state").write_text(state)
        if latest:
            (self.tmp / "latest").write_text(latest + "\n")
        env = {"PATH": f"{self.tmp / 'bin'}:/usr/bin:/bin", "FAKE_DIR": str(self.tmp), "TAG": tag,
               "PRERELEASE_INPUT": prerelease, "ALLOW_OLDER": allow_older, "GITHUB_REPOSITORY": "example/product",
               "GITHUB_OUTPUT": str(self.tmp / "out")}
        r = subprocess.run(["bash", "-e", str(self.tmp / "step.sh")], cwd=self.tmp, env=env,
                           capture_output=True, text=True)
        calls = (self.tmp / "calls").read_text() if (self.tmp / "calls").exists() else ""
        return r, calls

    def test_a_new_release_is_drafted_then_published_not_prerelease(self):
        r, calls = self.run_step("v1.2.3")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("release create v1.2.3", calls)
        self.assertIn("--draft", calls)
        self.assertIn("release edit v1.2.3 --draft=false --prerelease=false", calls)

    def test_a_beta_tag_is_published_as_prerelease(self):
        r, calls = self.run_step("v0.5.4-beta.1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--prerelease=true", calls)

    def test_an_explicit_choice_overrides_auto(self):
        r, calls = self.run_step("v0.5.4-beta.1", prerelease="false")
        self.assertIn("--prerelease=false", calls)

    def test_an_rc_tag_is_refused(self):
        r, calls = self.run_step("v1.2.3-rc.1")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("release create", calls)

    def test_a_published_release_is_never_rewritten(self):
        r, calls = self.run_step("v1.2.3", state="published")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("release upload", calls)
        self.assertNotIn("--draft=false", calls)

    def test_a_draft_is_completed(self):
        r, calls = self.run_step("v1.2.3", state="draft")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("release upload v1.2.3", calls)
        self.assertIn("--draft=false", calls)

    def test_a_release_older_than_the_latest_is_refused_before_anything_is_written(self):
        for tag, latest in [("v0.10.0", "v0.11.0"), ("v0.9.0", "v0.10.0"), ("v1.2.3", "v1.2.4")]:
            with self.subTest(tag=tag, latest=latest):
                (self.tmp / "calls").unlink(missing_ok=True)
                r, calls = self.run_step(tag, latest=latest)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("not newer than the latest release", r.stdout + r.stderr)
                self.assertNotIn("release create", calls)
                self.assertNotIn("--draft=false", calls)

    def test_a_newer_release_is_published_as_latest(self):
        r, calls = self.run_step("v0.12.0", latest="v0.11.0")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("release edit v0.12.0 --draft=false --prerelease=false", calls)
        self.assertNotIn("--latest=false", calls)
        r, calls = self.run_step("v0.10.0", latest="v0.9.12")
        self.assertEqual(r.returncode, 0, r.stderr + " (numeric, not lexical)")

    def test_the_first_release_has_no_latest_to_compare(self):
        r, calls = self.run_step("v0.1.0")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_allow_older_publishes_without_making_it_latest(self):
        r, calls = self.run_step("v0.10.1", latest="v0.11.0", allow_older="true")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("release edit v0.10.1 --draft=false --prerelease=false --latest=false", calls)

    def test_a_prerelease_never_competes_for_latest(self):
        r, calls = self.run_step("v0.5.4-beta.1", latest="v0.6.0")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--prerelease=true", calls)


if __name__ == "__main__":
    unittest.main()
