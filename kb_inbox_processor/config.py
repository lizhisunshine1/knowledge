from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import CardType, Topic


TOPICS: dict[str, Topic] = {
    "01_底层原理": Topic(
        key="01_底层原理",
        label="底层原理",
        directory="01_底层原理",
        moc_file="00_MOC-底层原理.md",
        description="思维模型、商业本质、认知升级、人性洞察",
    ),
    "02_商业化与创业": Topic(
        key="02_商业化与创业",
        label="商业化与创业",
        directory="02_商业化与创业",
        moc_file="00_MOC-商业化与创业.md",
        description="商业模式、创业方法论、获客、运营",
    ),
    "03_AI与计算机": Topic(
        key="03_AI与计算机",
        label="AI与计算机",
        directory="03_AI与计算机",
        moc_file="00_MOC-AI与计算机.md",
        description="AI技术、工具、趋势、技术岗位",
    ),
    "04_自媒体创业": Topic(
        key="04_自媒体创业",
        label="自媒体创业",
        directory="04_自媒体创业",
        moc_file="00_MOC-自媒体创业.md",
        description="内容创作、流量、个人IP",
    ),
    "05_AI解决方案工作": Topic(
        key="05_AI解决方案工作",
        label="AI解决方案工作",
        directory="05_AI解决方案工作",
        moc_file="00_MOC-AI解决方案工作.md",
        description="售前咨询、方案设计、行业实践",
    ),
}


CARD_TYPES: dict[str, CardType] = {
    "C": CardType(
        key="C",
        label="概念",
        emoji="🧠",
        directory="01_概念卡",
        template_file="T-概念卡.md",
        moc_heading="### 🧠 概念卡",
        sections=(
            "定义",
            "通俗解释",
            "核心价值",
            "常见误区",
            "与哪些概念相关",
            "在哪些项目中会用到",
            "我的理解",
            "原始来源",
            "可进一步提炼为",
        ),
    ),
    "M": CardType(
        key="M",
        label="方法",
        emoji="🔧",
        directory="02_方法卡",
        template_file="T-方法卡.md",
        moc_heading="### 🔧 方法卡",
        sections=(
            "解决什么问题",
            "适用场景",
            "操作步骤",
            "使用条件",
            "注意事项",
            "例子",
            "可复用到哪些地方",
            "相关资源",
            "我的版本",
            "下一步优化",
        ),
    ),
    "A": CardType(
        key="A",
        label="案例",
        emoji="📖",
        directory="03_案例卡",
        template_file="T-案例卡.md",
        moc_heading="### 📖 案例卡",
        sections=(
            "案例背景",
            "发生了什么",
            "为什么成功 / 失败",
            "关键变量",
            "可复用的经验",
            "可迁移到哪些项目",
            "我的启发",
            "相关链接",
            "可提炼的模板",
        ),
    ),
    "Q": CardType(
        key="Q",
        label="问题",
        emoji="❓",
        directory="04_问题卡",
        template_file="T-问题卡.md",
        moc_heading="### ❓ 问题卡",
        sections=(
            "问题定义",
            "这个问题为什么重要",
            "常见答案",
            "我的判断标准",
            "可操作步骤",
            "相关知识",
            "我当前的结论",
            "后续需要验证",
            "对应项目",
        ),
    ),
    "P": CardType(
        key="P",
        label="原则",
        emoji="⚖️",
        directory="06_原则卡",
        template_file="T-原则卡.md",
        moc_heading="### ⚖️ 原则卡",
        sections=(
            "原则是什么",
            "这个原则的目的",
            "为什么它重要",
            "适用场景",
            "决策时优先级",
            "典型判断标准",
            "反例 / 不适用情况",
            "相关原则",
            "相关方法",
            "我的执行版本",
            "最近一次使用",
        ),
    ),
}


@dataclass
class ProcessorConfig:
    inbox_dir: str = "00_Inbox"
    resources_dir: str = "03_Resources"
    templates_dir: str = "_Templates"
    todelete_dir: str = "todelete"
    index_file: str = "index.md"
    log_file: str = "log.md"
    min_chars: int = 500
    model: str = "default"
    base_url: str = "http://localhost:8000/v1"
    api_key: str = "dummy"
    temperature: float = 0.2
    max_tokens: int = 5000
    max_cards: int = 6
    short_action: str = "move"
    keep_source: bool = False

    @classmethod
    def load(cls, root: Path, config_path: Path | None = None) -> "ProcessorConfig":
        path = config_path or root / "kb_processor_config.json"
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        values = {key: value for key, value in data.items() if key in allowed}
        return cls(**values)


def topic_path(root: Path, config: ProcessorConfig, topic_key: str) -> Path:
    return root / config.resources_dir / TOPICS[topic_key].directory


def normalize_topic(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if text in TOPICS:
        return text
    for key, topic in TOPICS.items():
        if text in {topic.label, topic.directory, key.replace("_", "")}:
            return key
    return None


def normalize_card_type(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip().upper()
    if text in CARD_TYPES:
        return text
    if text.startswith("C") or "概念" in text:
        return "C"
    if text.startswith("M") or "方法" in text:
        return "M"
    if text.startswith("A") or "案例" in text:
        return "A"
    if text.startswith("Q") or "问题" in text:
        return "Q"
    if text.startswith("P") or "原则" in text:
        return "P"
    return None
