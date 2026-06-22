from __future__ import annotations

import re
from pathlib import Path

from .config import ProcessorConfig
from .models import InboxItem


TIMESTAMP_PREFIX_RE = re.compile(r"^\d{8,14}[_\-\s]+")
WINDOWS_INVALID_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def strip_timestamp(stem: str) -> str:
    title = TIMESTAMP_PREFIX_RE.sub("", stem).strip()
    return title or stem.strip()


def safe_filename(name: str, fallback: str = "未命名") -> str:
    cleaned = WINDOWS_INVALID_CHARS_RE.sub("-", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    cleaned = cleaned.replace("\u200b", "")
    return cleaned[:120] or fallback


def count_chars(text: str) -> int:
    return len(text)


def _is_processable_markdown(path: Path) -> bool:
    return path.suffix.lower() == ".md" and path.name.lower() != "readme.md"


def _has_assets(md_path: Path) -> bool:
    for child in md_path.parent.iterdir():
        if child == md_path:
            continue
        if child.is_dir() and child.name.lower() != "__pycache__":
            return True
        if child.is_file() and child.suffix.lower() != ".md":
            return True
    return False


def _source_unit(md_path: Path, inbox_root: Path) -> tuple[Path, bool]:
    sibling_mds = [p for p in md_path.parent.glob("*.md") if _is_processable_markdown(p)]
    if md_path.parent != inbox_root and len(sibling_mds) == 1:
        return md_path.parent, True
    return md_path, False


def scan_inbox(root: Path, config: ProcessorConfig) -> list[InboxItem]:
    inbox_root = root / config.inbox_dir
    if not inbox_root.exists():
        return []

    items: list[InboxItem] = []
    for md_path in inbox_root.rglob("*.md"):
        if not _is_processable_markdown(md_path):
            continue
        content = md_path.read_text(encoding="utf-8")
        title = safe_filename(strip_timestamp(md_path.stem), fallback=md_path.stem)
        source_unit, move_whole_dir = _source_unit(md_path, inbox_root)
        items.append(
            InboxItem(
                md_path=md_path,
                inbox_root=inbox_root,
                source_unit=source_unit,
                move_whole_dir=move_whole_dir,
                title=title,
                raw_title=md_path.stem,
                char_count=count_chars(content),
                has_assets=_has_assets(md_path),
            )
        )

    items.sort(key=lambda item: (-item.char_count, str(item.relative_md_path)))
    return items
