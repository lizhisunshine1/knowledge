from __future__ import annotations

import re

from .models import Anchor


BLOCK_ID_RE = re.compile(r"\^s[A-Za-z0-9_-]+")
ATX_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
BOLD_HEADING_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*[^*].*?\*\*|__[^_].*?__)\s*[:：]?\s*$")
NOISE_HEADING_KEYWORDS = ("推荐阅读", "品牌推广", "培训合作", "转载开白")


def _strip_inline_markdown(text: str) -> str:
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text).strip()
    text = text.strip("*_`# ")
    text = BLOCK_ID_RE.sub("", text).strip()
    return text


def _detect_heading(line: str, in_code: bool) -> tuple[int, str, str] | None:
    if in_code:
        return None
    atx = ATX_HEADING_RE.match(line)
    if atx:
        title = _strip_inline_markdown(atx.group(2))
        if _looks_like_noise_heading(line, title):
            return None
        return len(atx.group(1)), title, "markdown"
    if BOLD_HEADING_RE.match(line):
        title = _strip_inline_markdown(line)
        if _looks_like_noise_heading(line, title):
            return None
        return 2, title, "bold"
    return None


def _looks_like_noise_heading(raw_line: str, title: str) -> bool:
    compact = title.strip()
    if not compact:
        return True
    if len(compact) > 120:
        return True
    if "![" in raw_line or "](" in raw_line or "http://" in raw_line or "https://" in raw_line:
        return True
    return any(keyword in compact for keyword in NOISE_HEADING_KEYWORDS)


def _existing_anchor(line: str) -> str | None:
    found = BLOCK_ID_RE.findall(line)
    return found[-1] if found else None


def add_heading_block_ids(content: str) -> tuple[str, list[Anchor]]:
    """Add block ids to every detected title line and return annotated content.

    The function only appends ASCII block ids and blank lines. It never rewrites
    the source wording. If no title-like line exists, it anchors the first
    non-empty non-code line so the mindmap still has a precise jump target.
    """
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    in_code = False
    anchors: list[Anchor] = []
    section_no = 0
    item_no = 0
    first_plain_line: int | None = None

    for index, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if first_plain_line is None and not in_code and line.strip():
            first_plain_line = index
        detected = _detect_heading(line, in_code)
        if not detected:
            continue

        level, title, kind = detected
        existing = _existing_anchor(line)
        if level <= 2 or section_no == 0:
            section_no += 1
            item_no = 1
        else:
            item_no += 1

        block_id = existing or f"^s{section_no}-{item_no}"
        if not existing:
            lines[index] = line.rstrip() + f" {block_id}"
        anchors.append(Anchor(block_id=block_id, line_no=index + 1, text=title, level=level, kind=kind))

    if not anchors and first_plain_line is not None:
        block_id = "^s1-1"
        line = lines[first_plain_line]
        existing = _existing_anchor(line)
        block_id = existing or block_id
        if not existing:
            lines[first_plain_line] = line.rstrip() + f" {block_id}"
        anchors.append(
            Anchor(
                block_id=block_id,
                line_no=first_plain_line + 1,
                text=_strip_inline_markdown(line)[:80] or "正文开头",
                level=1,
                kind="first_line",
            )
        )

    if anchors:
        anchor_lines = {anchor.line_no - 1 for anchor in anchors}
        index = 0
        while index < len(lines):
            if index in anchor_lines:
                next_index = index + 1
                if next_index < len(lines) and lines[next_index].strip() != "":
                    lines.insert(next_index, "")
                    anchor_lines = {line_no + 1 if line_no >= next_index else line_no for line_no in anchor_lines}
                    index += 1
            index += 1

    return "\n".join(lines), anchors


def extract_block_ids(content: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for match in BLOCK_ID_RE.finditer(content):
        block_id = match.group(0)
        if block_id not in seen:
            seen.add(block_id)
            ordered.append(block_id)
    return ordered


def validate_block_ids(content: str) -> list[str]:
    issues: list[str] = []
    for match in BLOCK_ID_RE.finditer(content):
        after = content[match.end() : match.end() + 3]
        if after and after[0] not in "\n\r":
            issues.append(f"{match.group(0)} 后面存在非换行字符")
            continue
        newline_count = 0
        pos = match.end()
        while pos + newline_count < len(content) and content[pos + newline_count] in "\n\r":
            newline_count += 1
        if newline_count < 2:
            issues.append(f"{match.group(0)} 后面缺少空行")
    return issues
