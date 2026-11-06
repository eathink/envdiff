import unittest

from envdiff.mask import fingerprint, is_secret_key, mask_value, secret_kinds


class SecretKeyTests(unittest.TestCase):
    def test_common_secret_names(self):
        for key in (
            "DB_PASSWORD",
            "API_KEY",
            "OPENAI_API_KEY",
            "GITHUB_TOKEN",
            "AWS_SECRET_ACCESS_KEY",
            "AUTH_TOKEN",
            "SESSION_ID",
            "PRIVATE_KEY",
            "CREDENTIALS",
            "PWD",
        ):
            with self.subTest(key=key):
                self.assertTrue(is_secret_key(key))

    def test_ordinary_names(self):
        for key in ("PATH", "MONKEY", "API_URL", "KEY_NAME", "AUTHOR", "HOST"):
            with self.subTest(key=key):
                self.assertFalse(is_secret_key(key))


class SecretValueTests(unittest.TestCase):
    def test_github_token(self):
        self.assertIn("github_token", secret_kinds("ghp_" + "a" * 36))

    def test_github_fine_grained_pat(self):
        self.assertIn("github_pat", secret_kinds("github_pat_" + "a" * 30))

    def test_openai_key(self):
        self.assertIn("openai_key", secret_kinds("sk-" + "a" * 32))

    def test_aws_access_key(self):
        self.assertIn("aws_access_key", secret_kinds("AKIA" + "A" * 16))

    def test_slack_token(self):
        self.assertIn("slack_token", secret_kinds("xoxb-1234567890-abcdef"))

    def test_private_key_block(self):
        self.assertIn(
            "private_key", secret_kinds("-----BEGIN RSA PRIVATE KEY-----")
        )

    def test_jwt(self):
        token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature123"
        self.assertIn("jwt", secret_kinds(token))

    def test_plain_value_has_no_kind(self):
        self.assertEqual(secret_kinds("http://localhost:8000"), [])


class MaskValueTests(unittest.TestCase):
    def test_does_not_leak_original(self):
        masked = mask_value("super-secret-value")
        self.assertNotIn("super", masked)
        self.assertNotIn("secret", masked)

    def test_keeps_length_and_fingerprint(self):
        value = "abcdef"
        masked = mask_value(value)
        self.assertIn("6c", masked)
        self.assertIn(fingerprint(value), masked)

    def test_deterministic(self):
        self.assertEqual(mask_value("x"), mask_value("x"))

    def test_different_values_differ(self):
        self.assertNotEqual(mask_value("a"), mask_value("b"))


if __name__ == "__main__":
    unittest.main()
