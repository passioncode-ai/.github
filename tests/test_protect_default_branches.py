"""scripts/protect-default-branches.py against a fake `gh`: creates the ruleset with exactly the
deletion and non_fast_forward rules on ~DEFAULT_BRANCH, changes nothing on a second run, and
reports a private repository on GitHub Free as NOT PROTECTED instead of claiming success."""
from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "protect-default-branches.py"
FAKE = textwrap.dedent('''\
    #!{py}
    import json, os, sys
    a = sys.argv[1:]; data = sys.stdin.read() if "--input" in a else ""
    st = json.load(open(os.environ["STATE"]))
    open(os.environ["LOG"], "a").write(json.dumps({{"argv": a, "stdin": data}}) + "\\n")
    path = next(x for x in a[1:] if "/" in x and not x.startswith("-"))
    method = a[a.index("-X") + 1] if "-X" in a else "GET"
    repo = "/".join(path.split("/")[1:3])
    if repo in st.get("private", []):
        print("Upgrade to GitHub Pro or make this repository public to enable this feature.", file=sys.stderr); sys.exit(1)
    if path.endswith("/rulesets") and method == "GET":
        print(json.dumps(st.get("rulesets", {{}}).get(repo, []))); sys.exit(0)
    if "/rulesets/" in path and method == "GET":
        print(json.dumps(st["detail"])); sys.exit(0)
    print("{{}}")
    ''')


class Protect(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory(); self.t = Path(self._t.name)
        (self.t / "bin").mkdir(); gh = self.t / "bin" / "gh"
        gh.write_text(FAKE.format(py=sys.executable)); gh.chmod(gh.stat().st_mode | stat.S_IXUSR)

    def tearDown(self):
        self._t.cleanup()

    def run_(self, state, *args):
        (self.t / "state.json").write_text(json.dumps(state))
        env = {"PATH": f"{self.t / 'bin'}:/usr/bin:/bin", "STATE": str(self.t / "state.json"), "LOG": str(self.t / "log")}
        r = subprocess.run([sys.executable, str(SCRIPT), *args], env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        log = [json.loads(l) for l in (self.t / "log").read_text().splitlines()] if (self.t / "log").exists() else []
        return r, log

    def test_creates_exactly_the_two_rules_on_the_default_branch(self):
        r, log = self.run_({}, "--repo", "o/a", "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        post = next(c for c in log if "POST" in c["argv"])
        body = json.loads(post["stdin"])
        self.assertEqual(sorted(x["type"] for x in body["rules"]), ["deletion", "non_fast_forward"])
        self.assertEqual(body["conditions"]["ref_name"]["include"], ["~DEFAULT_BRANCH"])
        self.assertEqual(body["bypass_actors"], [])
        self.assertEqual(body["enforcement"], "active")

    def test_a_second_run_changes_nothing(self):
        detail = {"enforcement": "active", "rules": [{"type": "non_fast_forward"}, {"type": "deletion"}],
                  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"]}}, "bypass_actors": []}
        r, log = self.run_({"rulesets": {"o/a": [{"id": 5, "name": "protect-default-branch"}]}, "detail": detail}, "--repo", "o/a", "--apply")
        self.assertIn("unchanged", r.stdout)
        self.assertFalse(any("-X" in c["argv"] for c in log))

    def test_a_private_free_repository_is_reported_not_protected(self):
        r, log = self.run_({"private": ["o/p"]}, "--repo", "o/p", "--apply")
        self.assertIn("NOT PROTECTED", r.stdout)
        self.assertIn("1 cannot be protected", r.stdout)
        self.assertFalse(any("-X" in c["argv"] for c in log))

    def test_dry_run_writes_nothing(self):
        r, log = self.run_({}, "--repo", "o/a")
        self.assertIn("would create", r.stdout)
        self.assertFalse(any("-X" in c["argv"] for c in log))


if __name__ == "__main__":
    unittest.main()
