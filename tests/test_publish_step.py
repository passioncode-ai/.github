"""The `Create the release` step of release-publish.yml, run with a fake `gh`.

Contract: a new tag becomes a draft and is then published; -alpha/-beta/-preview tags are marked
prerelease under `auto`; an -rc tag is refused (rehearsals never publish); a published
release is never rewritten; a draft is completed.
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

    def run_step(self, tag: str, state: str = "absent", prerelease: str = "auto"):
        (self.tmp / "state").write_text(state)
        env = {"PATH": f"{self.tmp / 'bin'}:/usr/bin:/bin", "FAKE_DIR": str(self.tmp), "TAG": tag,
               "PRERELEASE_INPUT": prerelease, "GITHUB_REPOSITORY": "example/product",
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


if __name__ == "__main__":
    unittest.main()
