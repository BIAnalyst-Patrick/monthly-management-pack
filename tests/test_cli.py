"""The documented CLI must not be able to overwrite the published pack.

A reader who follows the README runs `python -m pack.report --month 2025-12`.
That must write somewhere disposable, not into the committed release artefacts.
"""

import contextlib
import hashlib
import io
import tempfile
import unittest
from pathlib import Path

from pack import cli

ROOT = Path(__file__).resolve().parent.parent


def _run(argv):
    """Call the CLI without printing its summary into the test log."""
    with contextlib.redirect_stdout(io.StringIO()) as buffer:
        code = cli.main(argv)
    return code, buffer.getvalue()


def _digest(directory: Path):
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


class DefaultRootTest(unittest.TestCase):
    def test_the_default_root_is_scratch_not_outputs(self):
        root = cli.default_root("2026-03")
        self.assertNotEqual(root, ROOT / "outputs")
        self.assertIn("scratch", root.parts)
        self.assertEqual(root.name, "2026-03")

    def test_scratch_is_ignored_by_git(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").split()
        self.assertIn("scratch/", ignored)


class RunTest(unittest.TestCase):
    def test_main_writes_into_the_requested_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "run"
            code, _ = _run(["--month", "2026-03", "--out", str(target)])
            self.assertEqual(code, 0)
            self.assertTrue((target / "outputs" / "MONTHLY_PACK.md").exists())
            self.assertTrue((target / "outputs" / "tables" / "line_variance.csv").exists())

    def test_main_leaves_the_committed_artefacts_alone(self):
        release = ROOT / "outputs"
        before = _digest(release)
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = _run(["--month", "2026-03", "--out", str(Path(tmp) / "run")])
        self.assertEqual(code, 0)
        self.assertEqual(before, _digest(release))

    def test_the_pack_it_writes_is_for_the_month_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "run"
            _, summary = _run(["--month", "2025-12", "--out", str(target)])
            self.assertIn("2025-12", summary)
            headline = (target / "outputs" / "MONTHLY_PACK.md").read_text().splitlines()[0]
        self.assertIn("2025-12", headline)

    def test_an_unknown_month_is_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "run"
            with self.assertRaises(KeyError):
                _run(["--month", "2024-01", "--out", str(target)])
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
