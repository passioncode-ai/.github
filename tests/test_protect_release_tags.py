"""scripts/protect-release-tags.py against a fake `gh`: creates the three tag rulesets (no deletion
of any `v*`, no update of any `v*` but `v1`, `v1` moved only by organization admins), changes
nothing on a second run, writes nothing on a dry run and never reports an unreadable repository
as protected."""
from __future__ import annotations

import importlib.util
import json
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "protect-release-tags.py"
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
        print(json.dumps(st.get("rulesets", []))); sys.exit(0)
    if "/rulesets/" in path and method == "GET":
        print(json.dumps(st["detail"][path.rsplit("/", 1)[1]])); sys.exit(0)
    if method == "POST":
        print(json.dumps({{"id": 900 + len(open(os.environ["LOG"]).readlines())}})); sys.exit(0)
    print("{{}}")
    ''')


def load():
    spec = importlib.util.spec_from_file_location("protect_release_tags", SCRIPT)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


class ProtectTags(unittest.TestCase):
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

    def posted(self, log):
        return {b["name"]: b for b in (json.loads(c["stdin"]) for c in log if "POST" in c["argv"])}

    def test_creates_the_three_tag_rulesets(self):
        r, log = self.run_({}, "--apply")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(all("repos/passioncode-ai/.github/rulesets" in " ".join(c["argv"]) for c in log))
        b = self.posted(log)
        self.assertEqual(set(b), {"release-tags-no-deletion", "release-tags-immutable", "floating-major-tag"})
        for body in b.values():
            self.assertEqual((body["target"], body["enforcement"]), ("tag", "active"))

    def test_no_v_tag_is_ever_deleted_not_even_v1_by_an_admin(self):
        _, log = self.run_({}, "--apply")
        body = self.posted(log)["release-tags-no-deletion"]
        self.assertEqual([x["type"] for x in body["rules"]], ["deletion"])
        self.assertEqual(body["conditions"]["ref_name"], {"include": ["refs/tags/v*"], "exclude": []})
        self.assertEqual(body["bypass_actors"], [])

    def test_a_published_version_tag_never_moves(self):
        _, log = self.run_({}, "--apply")
        body = self.posted(log)["release-tags-immutable"]
        self.assertEqual([x["type"] for x in body["rules"]], ["update"])
        self.assertEqual(body["conditions"]["ref_name"], {"include": ["refs/tags/v*"], "exclude": ["refs/tags/v1"]})
        self.assertEqual(body["bypass_actors"], [])

    def test_only_organization_admins_move_v1(self):
        _, log = self.run_({}, "--apply")
        body = self.posted(log)["floating-major-tag"]
        self.assertEqual([x["type"] for x in body["rules"]], ["update"])
        self.assertEqual(body["conditions"]["ref_name"]["include"], ["refs/tags/v1"])
        self.assertEqual([(a["actor_type"], a["bypass_mode"]) for a in body["bypass_actors"]],
                         [("OrganizationAdmin", "always")])

    def test_a_second_run_changes_nothing(self):
        mod = load()
        listing = [{"id": 10 + i, "name": d["name"]} for i, d in enumerate(mod.DESIRED)]
        detail = {str(10 + i): d for i, d in enumerate(mod.DESIRED)}
        r, log = self.run_({"rulesets": listing, "detail": detail}, "--apply")
        self.assertEqual(r.stdout.count("unchanged"), 3, r.stdout)
        self.assertFalse(any("-X" in c["argv"] for c in log))

    def test_a_drifted_ruleset_is_put_back(self):
        mod = load()
        listing = [{"id": 10 + i, "name": d["name"]} for i, d in enumerate(mod.DESIRED)]
        detail = {str(10 + i): d for i, d in enumerate(mod.DESIRED)}
        detail["12"] = dict(detail["12"], bypass_actors=[{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}])
        r, log = self.run_({"rulesets": listing, "detail": detail}, "--apply")
        puts = [c for c in log if "PUT" in c["argv"]]
        self.assertEqual(len(puts), 1)
        self.assertIn("repos/passioncode-ai/.github/rulesets/12", puts[0]["argv"])
        self.assertIn("floating-major-tag (12): updated", r.stdout)

    def test_dry_run_writes_nothing(self):
        r, log = self.run_({})
        self.assertEqual(r.stdout.count("would create"), 3, r.stdout)
        self.assertFalse(any("-X" in c["argv"] for c in log))

    def test_an_unreadable_repository_fails_instead_of_passing(self):
        r, log = self.run_({"private": ["o/p"]}, "--repo", "o/p", "--apply")
        self.assertIn("NOT PROTECTED", r.stdout)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(any("-X" in c["argv"] for c in log))


if __name__ == "__main__":
    unittest.main()
