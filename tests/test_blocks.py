import unittest

from kb_inbox_processor.blocks import add_heading_block_ids, extract_block_ids, validate_block_ids


class BlockIdTests(unittest.TestCase):
    def test_adds_ids_to_markdown_headings(self):
        content = "# 标题\n正文\n\n## 小节\n内容"
        annotated, anchors = add_heading_block_ids(content)
        self.assertIn("# 标题 ^s1-1\n\n正文", annotated)
        self.assertIn("## 小节 ^s2-1\n\n内容", annotated)
        self.assertEqual([anchor.block_id for anchor in anchors], ["^s1-1", "^s2-1"])
        self.assertEqual(validate_block_ids(annotated), [])

    def test_anchors_first_line_when_no_heading(self):
        annotated, anchors = add_heading_block_ids("第一段正文\n第二段")
        self.assertIn("第一段正文 ^s1-1\n\n第二段", annotated)
        self.assertEqual(len(anchors), 1)
        self.assertEqual(extract_block_ids(annotated), ["^s1-1"])

    def test_preserves_existing_ids(self):
        annotated, anchors = add_heading_block_ids("# 标题 ^s9-1\n\n正文")
        self.assertIn("# 标题 ^s9-1", annotated)
        self.assertEqual(anchors[0].block_id, "^s9-1")


if __name__ == "__main__":
    unittest.main()
