import unittest

from kb_inbox_processor.scanner import safe_filename, strip_timestamp


class ScannerTests(unittest.TestCase):
    def test_strip_timestamp(self):
        self.assertEqual(strip_timestamp("20260312130153_从现在开始"), "从现在开始")
        self.assertEqual(strip_timestamp("普通标题"), "普通标题")

    def test_safe_filename(self):
        self.assertEqual(safe_filename('A:B/C*D?'), "A-B-C-D-")


if __name__ == "__main__":
    unittest.main()
