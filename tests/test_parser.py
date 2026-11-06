import tempfile
import unittest
from pathlib import Path

from envdiff.parser import ParseError, load_path, parse_dotenv, parse_json


class DotenvTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(
            parse_dotenv("A=1\nB=hello\n"), {"A": "1", "B": "hello"}
        )

    def test_comments_and_blank_lines(self):
        text = "# 注释\n\nA=1\n   \n# 尾注释\nB=2\n"
        self.assertEqual(parse_dotenv(text), {"A": "1", "B": "2"})

    def test_export_prefix(self):
        self.assertEqual(parse_dotenv("export A=1\n"), {"A": "1"})

    def test_double_quotes_escape(self):
        self.assertEqual(
            parse_dotenv(r'MSG="line1\nline2"'), {"MSG": "line1\nline2"}
        )

    def test_double_quotes_escaped_quote(self):
        self.assertEqual(parse_dotenv(r'A="say \"hi\""'), {"A": 'say "hi"'})

    def test_single_quotes_are_literal(self):
        self.assertEqual(parse_dotenv(r"A='a\nb'"), {"A": r"a\nb"})

    def test_inline_comment(self):
        self.assertEqual(parse_dotenv("A=hello # note"), {"A": "hello"})

    def test_hash_inside_quotes_is_kept(self):
        self.assertEqual(parse_dotenv('A="x # y"'), {"A": "x # y"})

    def test_quoted_value_with_trailing_comment(self):
        self.assertEqual(parse_dotenv('A="x" # note'), {"A": "x"})

    def test_empty_value(self):
        self.assertEqual(parse_dotenv("A=\n"), {"A": ""})

    def test_value_with_spaces(self):
        self.assertEqual(parse_dotenv("A=hello world"), {"A": "hello world"})

    def test_invalid_line_reports_line_number(self):
        with self.assertRaises(ParseError) as ctx:
            parse_dotenv("A=1\nJUSTAKEY\n")
        self.assertIn(":2:", str(ctx.exception))

    def test_invalid_key_rejected(self):
        with self.assertRaises(ParseError):
            parse_dotenv("1BAD=x")

    def test_unclosed_quote_rejected(self):
        with self.assertRaises(ParseError):
            parse_dotenv('A="oops')

    def test_extra_content_after_quote_rejected(self):
        with self.assertRaises(ParseError):
            parse_dotenv('A="x"y')


class JsonTests(unittest.TestCase):
    def test_scalars_are_stringified(self):
        text = '{"A": 1, "B": true, "C": null, "D": "x"}'
        self.assertEqual(
            parse_json(text), {"A": "1", "B": "true", "C": "", "D": "x"}
        )

    def test_nested_object_rejected(self):
        with self.assertRaises(ParseError):
            parse_json('{"A": {"B": "x"}}')

    def test_array_rejected(self):
        with self.assertRaises(ParseError):
            parse_json('["A"]')

    def test_invalid_json_reports_position(self):
        with self.assertRaises(ParseError) as ctx:
            parse_json('{"A": }')
        self.assertIn(":1:", str(ctx.exception))


class LoadPathTests(unittest.TestCase):
    def test_loads_by_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / "a.env"
            env.write_text("A=1\n", encoding="utf-8")
            cfg = Path(tmp) / "a.json"
            cfg.write_text('{"A": 2}', encoding="utf-8")
            self.assertEqual(load_path(str(env)), {"A": "1"})
            self.assertEqual(load_path(str(cfg)), {"A": "2"})

    def test_missing_file_rejected(self):
        with self.assertRaises(ParseError):
            load_path("/nonexistent/.env")


if __name__ == "__main__":
    unittest.main()
