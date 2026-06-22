from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .config import CARD_TYPES, TOPICS, ProcessorConfig, topic_path
from .fsops import DryRunRecorder, atomic_write_text
from .models import CardWrite, ProcessResult
from .render import vault_relative, wikilink


INDEX_START = "<!-- kb-inbox-processor:index:start -->"
INDEX_END = "<!-- kb-inbox-processor:index:end -->"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _count_md(path: Path, recursive: bool = True) -> int:
    if not path.exists():
        return 0
    iterator = path.rglob("*.md") if recursive else path.glob("*.md")
    return sum(1 for item in iterator if item.name.lower() != "readme.md")


def collect_stats(root: Path, config: ProcessorConfig) -> dict[str, object]:
    excluded = {".git", ".obsidian", "__pycache__", config.todelete_dir}
    total_pages = 0
    for md in root.rglob("*.md"):
        if any(part in excluded for part in md.relative_to(root).parts):
            continue
        total_pages += 1

    topic_stats: dict[str, dict[str, int]] = {}
    totals = {"C": 0, "M": 0, "A": 0, "Q": 0, "P": 0, "inbox": 0, "abstract": 0}
    for topic_key in TOPICS:
        base = topic_path(root, config, topic_key)
        stats: dict[str, int] = {}
        for card_key, card_type in CARD_TYPES.items():
            count = _count_md(base / card_type.directory)
            stats[card_key] = count
            totals[card_key] += count
        stats["inbox"] = _count_md(base / "inbox")
        stats["abstract"] = _count_md(base / "abstract")
        totals["inbox"] += stats["inbox"]
        totals["abstract"] += stats["abstract"]
        topic_stats[topic_key] = stats
    return {"total_pages": total_pages, "topics": topic_stats, "totals": totals}


def _append_under_heading(content: str, heading: str, line: str) -> str:
    if line in content:
        return content
    escaped = re.escape(heading)
    match = re.search(rf"^{escaped}.*$", content, flags=re.MULTILINE)
    if not match:
        return content.rstrip() + f"\n\n{heading}\n{line}\n"

    level = len(heading) - len(heading.lstrip("#"))
    next_heading = re.search(rf"\n#{{1,{level}}}\s+", content[match.end() :])
    if next_heading:
        insert_at = match.end() + next_heading.start()
        return content[:insert_at].rstrip() + f"\n{line}\n\n" + content[insert_at:].lstrip("\n")
    return content.rstrip() + f"\n{line}\n"


def update_moc(
    root: Path,
    config: ProcessorConfig,
    result: ProcessResult,
    source_rel_no_ext: str,
    mindmap_rel_no_ext: str,
    card_writes: list[CardWrite],
    dry_run: DryRunRecorder,
) -> None:
    if not result.topic_key:
        return
    topic = TOPICS[result.topic_key]
    moc_path = topic_path(root, config, result.topic_key) / topic.moc_file
    content = _read(moc_path) or f"# 00_MOC-{topic.label}\n"
    content = _append_under_heading(
        content,
        "## 📥 原文资料",
        f"- {wikilink(source_rel_no_ext)} — {result.reason or result.item_title}",
    )
    content = _append_under_heading(
        content,
        "## 📝 摘要/思维导图",
        f"- {wikilink(mindmap_rel_no_ext)} — {result.nodes_count}节点·{result.reason or result.item_title}",
    )
    for write in card_writes:
        card_type = CARD_TYPES[write.draft.type_key]
        content = _append_under_heading(
            content,
            card_type.moc_heading,
            f"- {wikilink(write.vault_link)} — {write.draft.one_line}",
        )
    atomic_write_text(moc_path, content, dry_run)


def _existing_recent_lines(content: str) -> list[str]:
    if INDEX_START not in content or INDEX_END not in content:
        return []
    block = content.split(INDEX_START, 1)[1].split(INDEX_END, 1)[0]
    return [line for line in block.splitlines() if line.startswith("- [")]


def _build_managed_index_block(
    root: Path,
    config: ProcessorConfig,
    stats: dict[str, object],
    recent_lines: list[str],
) -> str:
    topic_stats = stats["topics"]
    totals = stats["totals"]
    lines = [
        INDEX_START,
        "## 🤖 自动导入索引",
        "",
        f"> 由 `kb_inbox_processor` 维护 | 最后更新: {date.today().isoformat()} | 共 {stats['total_pages']} 个页面",
        "",
        "### 资源统计",
        "",
    ]
    for topic_key, topic in TOPICS.items():
        s = topic_stats[topic_key]  # type: ignore[index]
        moc_rel = vault_relative(topic_path(root, config, topic_key) / topic.moc_file, root)
        lines.append(
            f"- {wikilink(moc_rel, topic.label)}: "
            f"C{s['C']} M{s['M']} A{s['A']} Q{s['Q']} P{s['P']} | "
            f"原文{s['inbox']} 摘要{s['abstract']}"
        )
    lines.extend(
        [
            "",
            "### 快速统计",
            "",
            f"- 概念卡: {totals['C']}",
            f"- 方法卡: {totals['M']}",
            f"- 案例卡: {totals['A']}",
            f"- 问题卡: {totals['Q']}",
            f"- 原则卡: {totals['P']}",
            f"- 原文: {totals['inbox']}",
            f"- 摘要/思维导图: {totals['abstract']}",
            "",
            "### 最近导入",
            "",
        ]
    )
    lines.extend(recent_lines[:50] or ["- 暂无"])
    lines.append(INDEX_END)
    return "\n".join(lines)


def update_index(
    root: Path,
    config: ProcessorConfig,
    result: ProcessResult,
    source_rel_no_ext: str,
    mindmap_rel_no_ext: str,
    card_writes: list[CardWrite],
    dry_run: DryRunRecorder,
) -> None:
    index_path = root / config.index_file
    content = _read(index_path)
    stats = collect_stats(root, config)
    today = date.today().isoformat()
    content = re.sub(
        r"> 自动生成 \| 最后更新: .*? \| 共 \d+ 个页面",
        f"> 自动生成 | 最后更新: {today} | 共 {stats['total_pages']} 个页面",
        content,
        count=1,
    )
    card_part = "，".join(wikilink(write.vault_link) for write in card_writes) or "无卡片"
    recent_line = f"- [{today}] {wikilink(source_rel_no_ext)} -> {wikilink(mindmap_rel_no_ext)}；{card_part}"
    recent_lines = [recent_line]
    for line in _existing_recent_lines(content):
        if line != recent_line and line not in recent_lines:
            recent_lines.append(line)
    managed_block = _build_managed_index_block(root, config, stats, recent_lines)
    if INDEX_START in content and INDEX_END in content:
        content = re.sub(
            rf"{re.escape(INDEX_START)}.*?{re.escape(INDEX_END)}",
            managed_block,
            content,
            flags=re.DOTALL,
        )
    else:
        content = content.rstrip() + "\n\n" + managed_block + "\n"
    atomic_write_text(index_path, content, dry_run)


def append_log(
    root: Path,
    config: ProcessorConfig,
    result: ProcessResult,
    source_rel_no_ext: str,
    mindmap_rel_no_ext: str,
    card_writes: list[CardWrite],
    dry_run: DryRunRecorder,
) -> None:
    path = root / config.log_file
    content = _read(path).rstrip()
    today = date.today().isoformat()
    card_names = "、".join(write.draft.name for write in card_writes) or "无卡片"
    entry = (
        f"## [{today}] ingest | {result.item_title} → {result.topic_key} "
        f"({result.anchors_count}个^s, {result.nodes_count}节点, {len(card_writes)}卡)\n"
        f"- 原文: {wikilink(source_rel_no_ext)}\n"
        f"- 思维导图: {wikilink(mindmap_rel_no_ext)}\n"
        f"- 卡片: {card_names}\n"
    )
    atomic_write_text(path, content + "\n\n" + entry if content else entry, dry_run)
