import unittest

from envdiff.diff import Status, diff_environments, has_differences, summarize


class DiffTests(unittest.TestCase):
    def test_statuses(self):
        entries = diff_environments(
            {"SAME": "x", "GONE": "1", "EDIT": "old"},
            {"SAME": "x", "NEW": "2", "EDIT": "new"},
        )
        by_key = {entry.key: entry for entry in entries}

        self.assertIs(by_key["SAME"].status, Status.SAME)
        self.assertIs(by_key["GONE"].status, Status.REMOVED)
        self.assertIs(by_key["NEW"].status, Status.ADDED)
        self.assertIs(by_key["EDIT"].status, Status.CHANGED)

    def test_removed_and_added_values(self):
        entries = diff_environments({"OLD": "1"}, {"NEW": "2"})
        by_key = {entry.key: entry for entry in entries}

        self.assertEqual(by_key["OLD"].left, "1")
        self.assertIsNone(by_key["OLD"].right)
        self.assertIsNone(by_key["NEW"].left)
        self.assertEqual(by_key["NEW"].right, "2")

    def test_sorted_by_key(self):
        entries = diff_environments({"C": "1", "A": "1"}, {"B": "1"})
        self.assertEqual([entry.key for entry in entries], ["A", "B", "C"])

    def test_summary(self):
        entries = diff_environments(
            {"SAME": "x", "GONE": "1", "EDIT": "old"},
            {"SAME": "x", "NEW": "2", "EDIT": "new"},
        )
        self.assertEqual(
            summarize(entries),
            {"added": 1, "removed": 1, "changed": 1, "same": 1},
        )

    def test_has_differences(self):
        self.assertFalse(has_differences(diff_environments({"A": "1"}, {"A": "1"})))
        self.assertTrue(has_differences(diff_environments({"A": "1"}, {"A": "2"})))


if __name__ == "__main__":
    unittest.main()
