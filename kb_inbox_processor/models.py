from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Topic:
    key: str
    label: str
    directory: str
    moc_file: str
    description: str


@dataclass(frozen=True)
class CardType:
    key: str
    label: str
    emoji: str
    directory: str
    template_file: str
    moc_heading: str
    sections: tuple[str, ...]


@dataclass(frozen=True)
class InboxItem:
    md_path: Path
    inbox_root: Path
    source_unit: Path
    move_whole_dir: bool
    title: str
    raw_title: str
    char_count: int
    has_assets: bool

    @property
    def relative_md_path(self) -> Path:
        return self.md_path.relative_to(self.inbox_root)

    @property
    def relative_source_unit(self) -> Path:
        return self.source_unit.relative_to(self.inbox_root)


@dataclass(frozen=True)
class Anchor:
    block_id: str
    line_no: int
    text: str
    level: int
    kind: str


@dataclass
class MindmapNode:
    title: str
    summary: str
    source_block_id: str
    card_names: list[str] = field(default_factory=list)


@dataclass
class MindmapSection:
    title: str
    nodes: list[MindmapNode] = field(default_factory=list)


@dataclass
class CardDraft:
    type_key: str
    name: str
    one_line: str
    source_block_id: str
    node_title: str
    sections: dict[str, str] = field(default_factory=dict)


@dataclass
class LLMDecision:
    keep: bool
    reason: str
    topic_key: str | None = None
    summary: str = ""
    mindmap: list[MindmapSection] = field(default_factory=list)
    cards: list[CardDraft] = field(default_factory=list)


@dataclass
class CardWrite:
    draft: CardDraft
    path: Path
    vault_link: str
    existed: bool = False


@dataclass
class ProcessResult:
    status: str
    item_title: str
    reason: str = ""
    topic_key: str | None = None
    source_path: Path | None = None
    mindmap_path: Path | None = None
    card_paths: list[Path] = field(default_factory=list)
    anchors_count: int = 0
    nodes_count: int = 0
