"""actions/release-guard/guard.py against a scripted fake `gh`.

The contract (docs/release-signing/DESIGN.md, "Approval by checks"): a tag release passes only
when main contains the tagged commit and every listed CI workflow's newest run on that commit
succeeded; a missing run is started on the tag and waited for; anything else refuses with a
reason; a ref that is not a tag passes as a rehearsal.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "actions" / "release-guard" / "guard.py"
REPO, SHA, TAG = "passioncode-ai/fabric-vr", "a" * 40, "v1.2.3"

# Each GET of a workflow's runs answers the next entry of that workflow's script (the last one
# repeats); a dispatch is logged and, when the script says so, makes the following GETs see a run.
FAKE = textwrap.dedent('''\
    #!{python}
    import json, os, sys
    argv = sys.argv[1:]
    state_path = os.environ["FAKE_GH_STATE"]
    state = json.load(open(state_path))
    with open(os.environ["FAKE_GH_LOG"], "a") as f:
        f.write(json.dumps(argv) + "\\n")
    path = next((a for a in argv[1:] if not a.startswith("-") and "/" in a), "")
    if "-X" in argv and argv[argv.index("-X") + 1] == "POST" and path.endswith("/dispatches"):
        wf = path.split("/workflows/")[1].split("/")[0]
        state["dispatched"].append(wf)
        state["runs"][wf] = state.get("after_dispatch", {{}}).get(wf, state["runs"].get(wf, [[]]))
        json.dump(state, open(state_path, "w")); sys.exit(0)
    if "/compare/" in path:
        if state.get("compare_error"):
            print("HTTP 404: Not Found", file=sys.stderr); sys.exit(1)
        print(json.dumps({{"status": state["compare"]}})); sys.exit(0)
    if "/actions/workflows/" in path and "/runs" in path:
        wf = path.split("/workflows/")[1].split("/")[0]
        script = state["runs"].get(wf, [[]])
        answer = script[0]
        if len(script) > 1:
            state["runs"][wf] = script[1:]
            json.dump(state, open(state_path, "w"))
        print(json.dumps({{"workflow_runs": answer}})); sys.exit(0)
    print("{{}}")
    ''')


def run_of(status: str, conclusion: str | None = None, created: str = "2026-10-11T10:00:00Z") -> dict:
    return {"status": status, "conclusion": conclusion, "created_at": created,
            "html_url": "https://github.com/x/y/actions/runs/1"}


class ReleaseGuard(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        gh = bin_dir / "gh"
        gh.write_text(FAKE.format(python=sys.executable))
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        self.path = f"{bin_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}"

    def tearDown(self):
        self._tmp.cleanup()

    def guard(self, state: dict, workflows: str = "ci.yml", ref: str = f"refs/tags/{TAG}", **extra):
        state = {"compare": "identical", "runs": {}, "dispatched": [], **state}
        (self.tmp / "state.json").write_text(json.dumps(state))
        env = {"PATH": self.path, "FAKE_GH_STATE": str(self.tmp / "state.json"),
               "FAKE_GH_LOG": str(self.tmp / "calls.jsonl"), "REPO": REPO, "REF": ref, "SHA": SHA,
               "WORKFLOWS": workflows, "POLL_SECONDS": "0", "GRACE_SECONDS": "0", "TIMEOUT_MINUTES": "0.02",
               "GITHUB_STEP_SUMMARY": str(self.tmp / "summary.md"), **extra}
        result = subprocess.run([sys.executable, str(GUARD)], env=env, capture_output=True, text=True, timeout=60)
        return result, json.loads((self.tmp / "state.json").read_text())

    def test_a_tag_on_main_with_green_ci_passes(self):
        result, _ = self.guard({"compare": "ahead", "runs": {"ci.yml": [[run_of("completed", "success")]]}})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("may sign and publish", result.stdout)
        self.assertIn("ci.yml: success", (self.tmp / "summary.md").read_text())

    def test_a_tag_off_main_is_refused_before_any_ci_is_read(self):
        result, _ = self.guard({"compare": "diverged", "runs": {"ci.yml": [[run_of("completed", "success")]]}})
        self.assertEqual(result.returncode, 1)
        self.assertIn("is not on main", result.stdout)
        calls = [json.loads(line) for line in (self.tmp / "calls.jsonl").read_text().splitlines()]
        self.assertFalse([c for c in calls if any("/runs" in a for a in c)], calls)

    def test_failed_ci_on_the_commit_is_refused_with_its_link(self):
        result, _ = self.guard({"runs": {"ci.yml": [[run_of("completed", "failure")]]}})
        self.assertEqual(result.returncode, 1)
        self.assertIn("ci.yml concluded failure", result.stdout)
        self.assertIn("actions/runs/1", result.stdout)

    def test_the_newest_run_decides(self):
        runs = [run_of("completed", "failure", "2026-10-11T09:00:00Z"), run_of("completed", "success", "2026-10-11T10:00:00Z")]
        result, _ = self.guard({"runs": {"ci.yml": [runs]}})
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_a_running_ci_is_waited_for(self):
        result, _ = self.guard({"runs": {"ci.yml": [[run_of("in_progress")], [run_of("in_progress")],
                                                    [run_of("completed", "success")]]}})
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_a_missing_run_is_started_on_the_tag_and_waited_for(self):
        result, state = self.guard({"runs": {"ci.yml": [[]]},
                                    "after_dispatch": {"ci.yml": [[run_of("queued")], [run_of("completed", "success")]]}})
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(state["dispatched"], ["ci.yml"])
        calls = [json.loads(line) for line in (self.tmp / "calls.jsonl").read_text().splitlines()]
        post = next(c for c in calls if "POST" in c)
        self.assertIn(f"ref={TAG}", post)

    def test_without_dispatch_a_missing_run_times_out_and_refuses(self):
        result, state = self.guard({"runs": {"ci.yml": [[]]}}, DISPATCH="false")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(state["dispatched"], [])
        self.assertIn("never ran", result.stdout)

    def test_every_listed_workflow_must_pass(self):
        result, _ = self.guard({"runs": {"ci.yml": [[run_of("completed", "success")]],
                                         "e2e.yml": [[run_of("completed", "cancelled")]]}}, workflows="ci.yml\ne2e.yml\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("e2e.yml concluded cancelled", result.stdout)

    def test_no_workflows_means_the_ancestry_check_alone(self):
        result, _ = self.guard({}, workflows="")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("own gate", (self.tmp / "summary.md").read_text())

    def test_a_branch_ref_passes_as_a_rehearsal_without_calling_github(self):
        result, _ = self.guard({"compare": "diverged"}, ref="refs/heads/main")
        self.assertEqual(result.returncode, 0)
        self.assertIn("rehearsal", result.stdout)
        self.assertFalse((self.tmp / "calls.jsonl").exists())

    def test_a_rehearsal_on_a_tag_off_main_passes_without_calling_github(self):
        result, _ = self.guard({"compare": "diverged"}, ref="refs/tags/v1.2.3-rc.1", PUBLISH="false")
        self.assertEqual(result.returncode, 0)
        self.assertIn("rehearsal", result.stdout)
        self.assertFalse((self.tmp / "calls.jsonl").exists())

    def test_an_unanswered_api_call_refuses_rather_than_passes(self):
        result, _ = self.guard({"compare_error": True})
        self.assertEqual(result.returncode, 1)
        self.assertIn("GitHub could not answer", result.stdout)


if __name__ == "__main__":
    unittest.main()
