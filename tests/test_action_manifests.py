"""Every action.yml in this repository must parse as YAML, and declare name, description and runs.

actionlint checks workflows, not action manifests: on 2026-10-03 an unquoted `if: always()`
in a description made `apple-signing/cleanup` unloadable, and every product's signing job
failed at "Set up job". Ruby's YAML (Psych) is on every macOS and Ubuntu runner and here.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUBY = 'require "yaml"; require "json"; puts JSON.generate(YAML.safe_load(File.read(ARGV[0])))'


@unittest.skipUnless(shutil.which("ruby"), "ruby is not installed")
class ActionManifests(unittest.TestCase):
    def test_every_action_manifest_parses_and_is_complete(self):
        manifests = sorted(ROOT.glob("actions/**/action.yml"))
        self.assertGreaterEqual(len(manifests), 4)
        for path in manifests:
            with self.subTest(action=str(path.relative_to(ROOT))):
                r = subprocess.run(["ruby", "-e", RUBY, str(path)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                doc = json.loads(r.stdout)
                self.assertIsInstance(doc, dict)
                for key in ("name", "description", "runs"):
                    self.assertIn(key, doc)
                self.assertEqual(doc["runs"]["using"], "composite")


if __name__ == "__main__":
    unittest.main()
