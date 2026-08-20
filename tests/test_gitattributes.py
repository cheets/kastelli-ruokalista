"""Guard the one thing the test suite cannot see: how git stores the feeds.

RFC 5545 requires CRLF, GitHub Pages serves the stored blob verbatim, and git's
default `text=auto` (plus a developer's `core.autocrlf=input`) silently rewrites
those CRLFs to LF on commit. `.gitattributes` is what prevents that, so it is
part of the deliverable and gets tested like any other part of it.
"""

import pathlib
import shutil
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
ATTRIBUTES = ROOT / ".gitattributes"


class GitAttributesTest(unittest.TestCase):
    def test_file_exists(self):
        self.assertTrue(ATTRIBUTES.exists(), ".gitattributes is required for CRLF safety")

    def test_ics_is_exempt_from_eol_conversion(self):
        rules = [
            line.split()
            for line in ATTRIBUTES.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        self.assertIn(["*.ics", "-text"], rules)


class GitCheckAttrTest(unittest.TestCase):
    """Ask git itself, so a contradicting later rule cannot slip through."""

    @unittest.skipUnless(shutil.which("git") and (ROOT / ".git").exists(), "needs a git repo")
    def test_git_reports_text_unset_for_the_ics_feed(self):
        result = subprocess.run(
            ["git", "check-attr", "text", "--", "docs/menu.ics"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("text: unset", result.stdout)


if __name__ == "__main__":
    unittest.main()
