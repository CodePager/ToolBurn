from __future__ import annotations

import contextlib
import io
import unittest

from toolburn.cli import main


class CliTests(unittest.TestCase):
    def test_help_returns_zero(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main([]), 0)
        self.assertIn("Local-first token burn profiler", stdout.getvalue())

    def test_planned_command_is_explicit(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main(["scan"]), 2)
        self.assertIn("planned for Phase 1", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
