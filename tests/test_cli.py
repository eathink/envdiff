import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from envdiff.cli import main


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name: str, text: str) -> str:
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_identical_files_exit_zero(self):
        left = self.write("left.env", "A=1\nB=2\n")
        right = self.write("right.env", "A=1\nB=2\n")

        code, out, _ = self.run_cli(left, right)

        self.assertEqual(code, 0)
        self.assertIn("没有差异", out)

    def test_differences_exit_one(self):
        left = self.write("left.env", "A=1\nB=old\n")
        right = self.write("right.env", "A=1\nC=3\nB=new\n")

        code, out, _ = self.run_cli(left, right)

        self.assertEqual(code, 1)
        self.assertIn("~ B", out)
        self.assertIn("+ C", out)

    def test_exit_zero_flag(self):
        left = self.write("left.env", "A=1\n")
        right = self.write("right.env", "A=2\n")

        code, _, _ = self.run_cli(left, right, "--exit-zero")

        self.assertEqual(code, 0)

    def test_secret_value_is_redacted(self):
        secret = "ghp_" + "a" * 36
        left = self.write("left.env", f"GITHUB_TOKEN={secret}\n")
        right = self.write("right.env", f"GITHUB_TOKEN={secret}x\n")

        code, out, _ = self.run_cli(left, right)

        self.assertEqual(code, 1)
        self.assertNotIn(secret, out)
        self.assertIn("<redacted:", out)

    def test_secret_key_is_redacted_even_with_plain_value(self):
        left = self.write("left.env", "DB_PASSWORD=hunter2\n")
        right = self.write("right.env", "DB_PASSWORD=hunter3\n")

        _, out, _ = self.run_cli(left, right)

        self.assertNotIn("hunter2", out)
        self.assertNotIn("hunter3", out)

    def test_no_mask_shows_original_and_warns(self):
        left = self.write("left.env", "DB_PASSWORD=hunter2\n")
        right = self.write("right.env", "DB_PASSWORD=hunter3\n")

        _, out, err = self.run_cli(left, right, "--no-mask")

        self.assertIn("hunter2", out)
        self.assertIn("警告", err)

    def test_json_format(self):
        left = self.write("left.env", "A=1\nB=2\n")
        right = self.write("right.env", "B=2\nC=3\n")

        _, out, _ = self.run_cli(left, right, "--format", "json")

        payload = json.loads(out)
        self.assertEqual(payload["summary"]["added"], 1)
        self.assertEqual(payload["summary"]["removed"], 1)
        self.assertEqual(payload["entries"][0]["key"], "A")
        self.assertFalse(payload["entries"][0]["masked"])

    def test_json_marks_masked_entries(self):
        left = self.write("left.env", "API_KEY=aaaabbbb\n")
        right = self.write("right.env", "API_KEY=ccccdddd\n")

        _, out, _ = self.run_cli(left, right, "--format", "json")

        entry = json.loads(out)["entries"][0]
        self.assertTrue(entry["masked"])
        self.assertNotIn("aaaabbbb", out)

    def test_all_shows_unchanged(self):
        left = self.write("left.env", "SAME=1\nDIFF=1\n")
        right = self.write("right.env", "SAME=1\nDIFF=2\n")

        _, out, _ = self.run_cli(left, right, "--all")

        self.assertIn("= SAME", out)

    def test_markdown_format(self):
        left = self.write("left.env", "A=1\n")
        right = self.write("right.env", "A=2\n")

        _, out, _ = self.run_cli(left, right, "--format", "markdown")

        self.assertIn("| 状态 | 变量 | 左 | 右 |", out)

    def test_missing_file_exit_two(self):
        existing = self.write("a.env", "A=1\n")

        code, _, err = self.run_cli(existing, str(self.tmp / "missing.env"))

        self.assertEqual(code, 2)
        self.assertIn("envdiff:", err)

    def test_include_filter(self):
        left = self.write("left.env", "APP_HOST=a\nDB_HOST=b\n")
        right = self.write("right.env", "APP_HOST=x\nDB_HOST=y\n")

        code, out, _ = self.run_cli(left, right, "--include", "APP_*")

        self.assertEqual(code, 1)
        self.assertIn("APP_HOST", out)
        self.assertNotIn("DB_HOST", out)

    def test_exclude_filter_can_clear_exit_code(self):
        left = self.write("left.env", "DEBUG=0\n")
        right = self.write("right.env", "DEBUG=1\n")

        code, out, _ = self.run_cli(left, right, "--exclude", "DEBUG")

        self.assertEqual(code, 0)
        self.assertIn("没有差异", out)

    def test_include_and_exclude_combined(self):
        left = self.write("left.env", "APP_HOST=a\nAPP_DEBUG=0\nDB_HOST=b\n")
        right = self.write("right.env", "APP_HOST=x\nAPP_DEBUG=1\nDB_HOST=y\n")

        _, out, _ = self.run_cli(
            left, right, "--include", "APP_*", "--exclude", "APP_DEBUG"
        )

        self.assertIn("APP_HOST", out)
        self.assertNotIn("APP_DEBUG", out)
        self.assertNotIn("DB_HOST", out)

    def test_filters_are_case_sensitive(self):
        left = self.write("left.env", "app_host=a\n")
        right = self.write("right.env", "app_host=b\n")

        code, _, _ = self.run_cli(left, right, "--include", "APP_*")

        self.assertEqual(code, 0)

    def test_fail_on_changed_only_ignores_added(self):
        left = self.write("left.env", "A=1\n")
        right = self.write("right.env", "A=1\nNEW=2\n")

        code, _, _ = self.run_cli(left, right, "--fail-on", "changed")

        self.assertEqual(code, 0)

    def test_fail_on_added_only_ignores_changed(self):
        left = self.write("left.env", "A=1\n")
        right = self.write("right.env", "A=2\n")

        code, _, _ = self.run_cli(left, right, "--fail-on", "added")

        self.assertEqual(code, 0)

    def test_fail_on_matching_status_still_fails(self):
        left = self.write("left.env", "A=1\nB=1\n")
        right = self.write("right.env", "A=2\n")

        code, _, _ = self.run_cli(left, right, "--fail-on", "removed")

        self.assertEqual(code, 1)

    def test_fail_on_none_never_fails(self):
        left = self.write("left.env", "A=1\n")
        right = self.write("right.env", "A=2\n")

        code, _, _ = self.run_cli(left, right, "--fail-on", "none")

        self.assertEqual(code, 0)

    def test_fail_on_multiple_statuses(self):
        left = self.write("left.env", "A=1\n")
        right = self.write("right.env", "A=1\nNEW=2\n")

        code, _, _ = self.run_cli(left, right, "--fail-on", "removed,added")

        self.assertEqual(code, 1)

    def test_fail_on_invalid_value_exits_two(self):
        left = self.write("left.env", "A=1\n")
        right = self.write("right.env", "A=1\n")

        with self.assertRaises(SystemExit) as ctx:
            with redirect_stderr(io.StringIO()):
                main([left, right, "--fail-on", "bogus"])

        self.assertEqual(ctx.exception.code, 2)

    def test_exit_zero_overrides_fail_on(self):
        left = self.write("left.env", "A=1\n")
        right = self.write("right.env", "A=2\n")

        code, _, _ = self.run_cli(left, right, "--fail-on", "changed", "--exit-zero")

        self.assertEqual(code, 0)

    def test_stdin_as_right(self):
        left = self.write("left.env", "A=1\nB=2\n")
        original = io.StringIO("A=1\n")

        import sys

        saved = sys.stdin
        try:
            sys.stdin = original
            code, out, _ = self.run_cli(left, "-")
        finally:
            sys.stdin = saved

        self.assertEqual(code, 1)
        self.assertIn("- B", out)

    def test_both_sides_stdin_rejected(self):
        code, _, err = self.run_cli("-", "-")

        self.assertEqual(code, 2)
        self.assertIn("不能同时为 -", err)

    def test_stdin_as_left(self):
        right = self.write("right.env", "A=1\nB=2\n")
        original = io.StringIO("A=1\n")

        import sys

        saved = sys.stdin
        try:
            sys.stdin = original
            code, out, _ = self.run_cli("-", right)
        finally:
            sys.stdin = saved

        self.assertEqual(code, 1)
        self.assertIn("+ B", out)


if __name__ == "__main__":
    unittest.main()
