from __future__ import annotations

from pathlib import Path

from .blocks import add_heading_block_ids, validate_block_ids
from .config import CARD_TYPES, ProcessorConfig, topic_path
from .fsops import DryRunRecorder, atomic_write_text, cleanup_source, copy_assets, move_to_todelete
from .indexing import append_log, update_index, update_moc
from .llm import OpenAIInboxAnalyzer, load_templates
from .models import CardDraft, CardWrite, InboxItem, LLMDecision, ProcessResult
from .render import card_filename, render_card, render_card_backlink, render_mindmap, vault_relative
from .scanner import safe_filename, scan_inbox


class ProcessingError(RuntimeError):
    pass


def _target_source_path(root: Path, config: ProcessorConfig, item: InboxItem, topic_key: str) -> Path:
    inbox_dir = topic_path(root, config, topic_key) / "inbox"
    if item.has_assets:
        return inbox_dir / item.title / f"{item.title}.md"
    return inbox_dir / f"{item.title}.md"


def _target_mindmap_path(root: Path, config: ProcessorConfig, title: str, topic_key: str) -> Path:
    return topic_path(root, config, topic_key) / "abstract" / f"思维导图：{safe_filename(title)}.md"


def _nodes_count(decision: LLMDecision) -> int:
    return sum(len(section.nodes) for section in decision.mindmap)


def _card_path(root: Path, config: ProcessorConfig, topic_key: str, draft: CardDraft) -> Path:
    card_type = CARD_TYPES[draft.type_key]
    return topic_path(root, config, topic_key) / card_type.directory / card_filename(draft)


def _prepare_card_writes(root: Path, config: ProcessorConfig, topic_key: str, decision: LLMDecision) -> list[CardWrite]:
    writes: list[CardWrite] = []
    seen: set[Path] = set()
    for draft in decision.cards:
        path = _card_path(root, config, topic_key, draft)
        if path in seen:
            continue
        seen.add(path)
        writes.append(
            CardWrite(
                draft=draft,
                path=path,
                vault_link=vault_relative(path, root),
                existed=path.exists(),
            )
        )
    return writes


def _write_cards(
    root: Path,
    source_rel_no_ext: str,
    mindmap_rel_no_ext: str,
    card_writes: list[CardWrite],
    dry_run: DryRunRecorder,
) -> None:
    for write in card_writes:
        if write.existed:
            existing = write.path.read_text(encoding="utf-8") if write.path.exists() else ""
            backlink = render_card_backlink(write.draft, source_rel_no_ext, mindmap_rel_no_ext)
            if backlink.strip() not in existing:
                atomic_write_text(write.path, existing.rstrip() + "\n" + backlink, dry_run)
            continue
        content = render_card(write.draft, source_rel_no_ext, mindmap_rel_no_ext)
        atomic_write_text(write.path, content, dry_run)


def _write_source_and_assets(item: InboxItem, target_source_path: Path, annotated_content: str, dry_run: DryRunRecorder) -> None:
    atomic_write_text(target_source_path, annotated_content, dry_run)
    if item.has_assets:
        copy_assets(item, target_source_path.parent, dry_run)


def process_item(
    root: Path,
    config: ProcessorConfig,
    analyzer: OpenAIInboxAnalyzer,
    templates: dict[str, str],
    item: InboxItem,
    dry_run: DryRunRecorder,
) -> ProcessResult:
    if item.char_count < config.min_chars:
        if config.short_action == "move":
            move_to_todelete(item, root / config.todelete_dir, dry_run)
        return ProcessResult(status="short_skipped", item_title=item.title, reason=f"字符数 {item.char_count} < {config.min_chars}")

    original = item.md_path.read_text(encoding="utf-8")
    annotated, anchors = add_heading_block_ids(original)
    issues = validate_block_ids(annotated)
    if issues:
        raise ProcessingError(f"{item.relative_md_path} 块标识校验失败: {'; '.join(issues[:3])}")

    decision = analyzer.analyze(item.title, item.char_count, anchors, annotated, templates)
    if not decision.keep:
        move_to_todelete(item, root / config.todelete_dir, dry_run)
        return ProcessResult(
            status="llm_skipped",
            item_title=item.title,
            reason=decision.reason,
            anchors_count=len(anchors),
        )

    if not decision.topic_key:
        raise ProcessingError("大模型判断 keep=true 但没有返回有效主题")

    target_source_path = _target_source_path(root, config, item, decision.topic_key)
    if target_source_path.exists():
        move_to_todelete(item, root / config.todelete_dir, dry_run)
        return ProcessResult(
            status="duplicate_skipped",
            item_title=item.title,
            reason=f"目标原文已存在: {target_source_path}",
            topic_key=decision.topic_key,
            anchors_count=len(anchors),
        )

    target_mindmap_path = _target_mindmap_path(root, config, item.title, decision.topic_key)
    source_rel_no_ext = vault_relative(target_source_path, root)
    mindmap_rel_no_ext = vault_relative(target_mindmap_path, root)
    card_writes = _prepare_card_writes(root, config, decision.topic_key, decision)

    _write_source_and_assets(item, target_source_path, annotated, dry_run)
    _write_cards(root, source_rel_no_ext, mindmap_rel_no_ext, card_writes, dry_run)
    mindmap = render_mindmap(item.title, decision, source_rel_no_ext, card_writes)
    atomic_write_text(target_mindmap_path, mindmap, dry_run)

    result = ProcessResult(
        status="ingested",
        item_title=item.title,
        reason=decision.summary or decision.reason,
        topic_key=decision.topic_key,
        source_path=target_source_path,
        mindmap_path=target_mindmap_path,
        card_paths=[write.path for write in card_writes],
        anchors_count=len(anchors),
        nodes_count=_nodes_count(decision),
    )
    update_moc(root, config, result, source_rel_no_ext, mindmap_rel_no_ext, card_writes, dry_run)
    update_index(root, config, result, source_rel_no_ext, mindmap_rel_no_ext, card_writes, dry_run)
    append_log(root, config, result, source_rel_no_ext, mindmap_rel_no_ext, card_writes, dry_run)

    if not config.keep_source:
        cleanup_source(item, dry_run)
    return result


def process_inbox(root: Path, config: ProcessorConfig, limit: int | None = None, dry_run_enabled: bool = False) -> tuple[list[ProcessResult], list[str]]:
    dry_run = DryRunRecorder(enabled=dry_run_enabled)
    templates = load_templates(root, config)
    analyzer = OpenAIInboxAnalyzer(config)
    items = scan_inbox(root, config)
    if limit is not None:
        items = items[:limit]

    results: list[ProcessResult] = []
    for item in items:
        try:
            results.append(process_item(root, config, analyzer, templates, item, dry_run))
        except Exception as exc:
            results.append(ProcessResult(status="error", item_title=item.title, reason=str(exc)))
    return results, dry_run.actions
