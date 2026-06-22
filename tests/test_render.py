import unittest
from pathlib import Path

from kb_inbox_processor.models import CardDraft, CardWrite, LLMDecision, MindmapNode, MindmapSection
from kb_inbox_processor.render import render_card, render_mindmap, vault_relative


class RenderTests(unittest.TestCase):
    def test_vault_relative_strips_md(self):
        root = Path("C:/kb")
        path = root / "03_Resources" / "01_底层原理" / "inbox" / "文章.md"
        self.assertEqual(vault_relative(path, root), "03_Resources/01_底层原理/inbox/文章")

    def test_card_contains_bidirectional_links(self):
        draft = CardDraft(
            type_key="C",
            name="C-测试概念",
            one_line="测试说明",
            source_block_id="^s1-1",
            node_title="测试节点",
            sections={"定义": "这是定义"},
        )
        content = render_card(draft, "03_Resources/01_底层原理/inbox/文章", "03_Resources/01_底层原理/abstract/思维导图：文章")
        self.assertIn("> 来自：[[03_Resources/01_底层原理/abstract/思维导图：文章#🎯 测试节点]]", content)
        self.assertIn("> 原文：[[03_Resources/01_底层原理/inbox/文章]]", content)
        self.assertIn("## 定义\n- 这是定义", content)

    def test_mindmap_links_to_source_block(self):
        draft = CardDraft(type_key="C", name="C-测试概念", one_line="测试说明", source_block_id="^s1-1", node_title="测试节点")
        decision = LLMDecision(
            keep=True,
            reason="值得入库",
            topic_key="01_底层原理",
            mindmap=[MindmapSection("一、主题", [MindmapNode("测试节点", "节点说明", "^s1-1", ["C-测试概念"])])],
            cards=[draft],
        )
        card_write = CardWrite(draft=draft, path=Path("x"), vault_link="03_Resources/01_底层原理/01_概念卡/C-测试概念")
        content = render_mindmap("文章", decision, "03_Resources/01_底层原理/inbox/文章", [card_write])
        self.assertIn("[[03_Resources/01_底层原理/inbox/文章#^s1-1]]", content)
        self.assertIn("[[03_Resources/01_底层原理/01_概念卡/C-测试概念]]", content)


if __name__ == "__main__":
    unittest.main()
