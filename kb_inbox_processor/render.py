from __future__ import annotations

import re
from pathlib import Path

from .config import CARD_TYPES
from .models import CardDraft, CardWrite, LLMDecision
from .scanner import safe_filename


def vault_relative(path: Path, root: Path, strip_md: bool = True) -> str:
    rel = path.relative_to(root).as_posix()
    if strip_md and rel.lower().endswith(".md"):
        rel = rel[:-3]
    return rel


def wikilink(path_or_target: str, alias: str | None = None) -> str:
    if alias:
        return f"[[{path_or_target}|{alias}]]"
    return f"[[{path_or_target}]]"


def block_link(source_rel_no_ext: str, block_id: str) -> str:
    return wikilink(f"{source_rel_no_ext}#{block_id}")


def heading_link(file_rel_no_ext: str, heading: str) -> str:
    return wikilink(f"{file_rel_no_ext}#{heading}")


def card_filename(draft: CardDraft) -> str:
    name = safe_filename(draft.name)
    if not name.upper().startswith(f"{draft.type_key}-"):
        name = f"{draft.type_key}-{name}"
    return f"{name}.md"


def _markdown_value(value: str) -> str:
    text = (value or "-").strip()
    if not text:
        return "-"
    if "\n" in text:
        return text
    if re.match(r"^(\d+\.|-|\*)\s+", text):
        return text
    return f"- {text}"


def _section_content(draft: CardDraft, heading: str, source_link: str, mindmap_node_link: str) -> str:
    direct = draft.sections.get(heading)
    if direct:
        return _markdown_value(direct)
    if heading in {"原始来源", "相关资源", "相关链接", "相关知识"}:
        return f"- {source_link}\n- {mindmap_node_link}"
    if heading in {"我的理解", "我的版本", "我的启发", "我当前的结论", "我的执行版本"}:
        return _markdown_value(draft.one_line)
    return "-"


def render_card(draft: CardDraft, source_rel_no_ext: str, mindmap_rel_no_ext: str) -> str:
    card_type = CARD_TYPES[draft.type_key]
    node_heading = f"🎯 {draft.node_title}"
    source_link = wikilink(source_rel_no_ext)
    mindmap_node_link = heading_link(mindmap_rel_no_ext, node_heading)
    lines = [
        f"> 来自：{mindmap_node_link}",
        f"> 原文：{source_link}",
        "",
        f"# {safe_filename(draft.name)}",
        "",
    ]
    for heading in card_type.sections:
        lines.append(f"## {heading}")
        lines.append(_section_content(draft, heading, source_link, mindmap_node_link))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_mindmap(
    title: str,
    decision: LLMDecision,
    source_rel_no_ext: str,
    card_writes: list[CardWrite],
) -> str:
    card_link_by_name = {write.draft.name: write.vault_link for write in card_writes}
    lines = [
        f"# 📐 思维导图：{title}",
        "",
        f"> 原文位置：{wikilink(source_rel_no_ext)}",
        f"> 入库判断：{decision.reason}",
        "",
        "---",
        "",
    ]

    for index, section in enumerate(decision.mindmap, start=1):
        section_title = section.title.strip() or f"第{index}部分"
        lines.append(f"## {section_title}")
        lines.append("")
        for node in section.nodes:
            node_title = node.title.strip() or "要点"
            lines.append(f"### 🎯 {node_title}")
            lines.append(f"- {node.summary} {block_link(source_rel_no_ext, node.source_block_id)}")
            for card_name in node.card_names:
                card_link = card_link_by_name.get(card_name)
                if card_link:
                    lines.append(f"- 🃏 {wikilink(card_link)}")
            for write in card_writes:
                if write.draft.node_title == node.title and write.vault_link not in [card_link_by_name.get(name) for name in node.card_names]:
                    lines.append(f"- 🃏 {wikilink(write.vault_link)}")
            lines.append("")

    if card_writes:
        lines.append("## 🔗 本篇文章提取的卡片")
        lines.append("")
        lines.append("| 卡片 | 类型 | 说明 |")
        lines.append("|------|:----:|------|")
        for write in card_writes:
            card_type = CARD_TYPES[write.draft.type_key]
            lines.append(f"| {wikilink(write.vault_link)} | {card_type.emoji} {card_type.label} | {write.draft.one_line} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_card_backlink(draft: CardDraft, source_rel_no_ext: str, mindmap_rel_no_ext: str) -> str:
    node_heading = f"🎯 {draft.node_title}"
    return (
        "\n## 关联来源\n"
        f"- 来自：{heading_link(mindmap_rel_no_ext, node_heading)}\n"
        f"- 原文：{wikilink(source_rel_no_ext)}\n"
    )
