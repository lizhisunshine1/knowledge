from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .config import CARD_TYPES, TOPICS, ProcessorConfig, normalize_card_type, normalize_topic
from .models import Anchor, CardDraft, LLMDecision, MindmapNode, MindmapSection


class LLMError(RuntimeError):
    pass


def health_url_from_base_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/health", "", "", ""))


def models_url_from_base_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/models"


def check_proxy_health(base_url: str, timeout: float = 2.0) -> None:
    health_url = health_url_from_base_url(base_url)
    models_url = models_url_from_base_url(base_url)
    try:
        with urllib.request.urlopen(health_url, timeout=timeout) as response:
            if response.status >= 400:
                raise LLMError(f"代理健康检查失败: HTTP {response.status} ({health_url})")
            return
    except urllib.error.URLError as exc:
        health_error = exc
    except TimeoutError as exc:
        health_error = exc

    try:
        with urllib.request.urlopen(models_url, timeout=timeout) as response:
            if response.status >= 400:
                raise LLMError(f"代理模型列表检查失败: HTTP {response.status} ({models_url})")
    except Exception as exc:
        raise LLMError(
            f"无法连接本地大模型代理: {health_url} 或 {models_url}。"
            f"请先启动代理服务。健康检查错误: {health_error}; 模型列表错误: {exc}"
        ) from exc


def load_templates(root: Path, config: ProcessorConfig) -> dict[str, str]:
    template_root = root / config.templates_dir
    templates: dict[str, str] = {}
    for card_type in CARD_TYPES.values():
        path = template_root / card_type.template_file
        if path.exists():
            templates[card_type.key] = path.read_text(encoding="utf-8")
    return templates


def _template_summary(templates: dict[str, str]) -> str:
    parts: list[str] = []
    for key, card_type in CARD_TYPES.items():
        headings = "、".join(card_type.sections)
        parts.append(f"{key}-{card_type.label}卡({card_type.directory}): {headings}")
    return "\n".join(parts)


def build_prompt(title: str, char_count: int, anchors: list[Anchor], annotated_content: str, templates: dict[str, str]) -> list[dict[str, str]]:
    topic_lines = "\n".join(
        f"- {topic.key}: {topic.label}，{topic.description}" for topic in TOPICS.values()
    )
    block_lines = "\n".join(f"- {anchor.block_id}: {anchor.text}" for anchor in anchors)
    card_types = "\n".join(
        f"- {card_type.key}: {card_type.label}卡，文件名前缀 {card_type.key}-，目录 {card_type.directory}"
        for card_type in CARD_TYPES.values()
    )

    schema = {
        "keep": True,
        "reason": "是否入库的判断原因，80字以内",
        "topic": "必须是五个主题目录之一，如 01_底层原理",
        "summary": "文章一句话摘要，30字以内",
        "mindmap": [
            {
                "section": "一级分支标题",
                "nodes": [
                    {
                        "title": "节点标题，短句",
                        "summary": "节点要点，50字以内",
                        "source_block_id": "^s1-1",
                        "cards": ["C-示例卡片名"],
                    }
                ],
            }
        ],
        "cards": [
            {
                "type": "C/M/A/Q/P",
                "name": "必须带前缀，如 C-概念名",
                "one_line": "15字以内说明",
                "source_block_id": "^s1-1",
                "node_title": "对应 mindmap 节点标题",
                "sections": {"定义": "按模板标题填写；不知道就写 -"},
            }
        ],
    }

    system = (
        "你是这个 Obsidian 知识库的入库判断与提炼助手。"
        "你只负责判断、分类、提炼思维导图和知识卡片内容；文件移动、块标识、链接和索引都由程序完成。"
        "必须只输出 JSON，不要输出 Markdown 代码块或解释文字。"
    )
    user = f"""请根据以下带 ^sX-Y 标识的原文，判断是否值得加入知识库，并提炼思维导图与知识卡片。

入库标准：
- 包含可迁移的思维模型、方法论、框架、原则、概念、问题或案例。
- 与商业、AI、创业、自媒体、解决方案工作等主题相关。
- 宁缺毋滥；没有独立价值就 keep=false。

五个主题：
{topic_lines}

可用卡片类型：
{card_types}

模板字段：
{_template_summary(templates)}

硬性规则：
- topic 必须使用五个主题目录原文。
- source_block_id 必须来自下方可用块 ID，不要虚构。
- cards 最多 6 张；每张卡片必须能独立复用。
- mindmap 的节点必须能单向链接回原文对应 block id。
- 卡片与思维导图要能双向链接，所以卡片必须填写 node_title 与 source_block_id。
- 如果 keep=false，mindmap 和 cards 返回空数组。
- 输出必须是一个 JSON 对象，符合这个形状：{json.dumps(schema, ensure_ascii=False)}

文章标题：{title}
字符数：{char_count}

可用块 ID：
{block_lines}

原文：
<<<ARTICLE
{annotated_content}
ARTICLE
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LLMError("大模型没有返回 JSON 对象")
        return json.loads(stripped[start : end + 1])


def _as_text(value: Any, default: str = "-") -> str:
    if value is None:
        return default
    if isinstance(value, list):
        return "\n".join(f"- {str(item).strip()}" for item in value if str(item).strip()) or default
    text = str(value).strip()
    return text or default


def parse_decision(data: dict[str, Any], valid_block_ids: set[str], max_cards: int) -> LLMDecision:
    keep = bool(data.get("keep"))
    reason = _as_text(data.get("reason"), default="")
    if not keep:
        return LLMDecision(keep=False, reason=reason or "大模型判断无入库价值")

    topic_key = normalize_topic(data.get("topic"))
    if not topic_key:
        raise LLMError(f"大模型返回了无效主题: {data.get('topic')!r}")

    fallback_block = next(iter(valid_block_ids), "^s1-1")

    mindmap: list[MindmapSection] = []
    for raw_section in data.get("mindmap", []) or []:
        section_title = _as_text(raw_section.get("section"), default="核心要点")
        nodes: list[MindmapNode] = []
        for raw_node in raw_section.get("nodes", []) or []:
            source_block_id = _as_text(raw_node.get("source_block_id"), default=fallback_block)
            if source_block_id not in valid_block_ids:
                source_block_id = fallback_block
            raw_cards = raw_node.get("cards", []) or []
            card_names = [str(card).strip() for card in raw_cards if str(card).strip()]
            nodes.append(
                MindmapNode(
                    title=_as_text(raw_node.get("title"), default="要点"),
                    summary=_as_text(raw_node.get("summary"), default="-"),
                    source_block_id=source_block_id,
                    card_names=card_names,
                )
            )
        if nodes:
            mindmap.append(MindmapSection(title=section_title, nodes=nodes))

    cards: list[CardDraft] = []
    for raw_card in (data.get("cards", []) or [])[:max_cards]:
        type_key = normalize_card_type(raw_card.get("type"))
        if not type_key:
            continue
        source_block_id = _as_text(raw_card.get("source_block_id"), default=fallback_block)
        if source_block_id not in valid_block_ids:
            source_block_id = fallback_block
        sections = raw_card.get("sections", {}) or {}
        if not isinstance(sections, dict):
            sections = {}
        card_name = _as_text(raw_card.get("name"), default=f"{type_key}-未命名")
        if not card_name.upper().startswith(f"{type_key}-"):
            card_name = f"{type_key}-{card_name}"
        cards.append(
            CardDraft(
                type_key=type_key,
                name=card_name,
                one_line=_as_text(raw_card.get("one_line"), default=reason[:15] or "-"),
                source_block_id=source_block_id,
                node_title=_as_text(raw_card.get("node_title"), default="要点"),
                sections={str(k).strip(): _as_text(v) for k, v in sections.items()},
            )
        )

    if not mindmap:
        mindmap = [
            MindmapSection(
                title="核心要点",
                nodes=[
                    MindmapNode(
                        title="文章主旨",
                        summary=_as_text(data.get("summary"), default=reason or "见原文"),
                        source_block_id=fallback_block,
                        card_names=[card.name for card in cards],
                    )
                ],
            )
        ]

    return LLMDecision(
        keep=True,
        reason=reason or "大模型判断值得入库",
        topic_key=topic_key,
        summary=_as_text(data.get("summary"), default=reason[:30] or "-"),
        mindmap=mindmap,
        cards=cards,
    )


class OpenAIInboxAnalyzer:
    def __init__(self, config: ProcessorConfig):
        self.config = config

    def analyze(self, title: str, char_count: int, anchors: list[Anchor], annotated_content: str, templates: dict[str, str]) -> LLMDecision:
        check_proxy_health(self.config.base_url)
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError("未安装 openai 包。请运行 pip install -r requirements.txt。") from exc

        client = OpenAI(base_url=self.config.base_url, api_key=self.config.api_key)
        messages = build_prompt(title, char_count, anchors, annotated_content, templates)
        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        text = response.choices[0].message.content or ""
        data = _extract_json_object(text)
        valid_block_ids = {anchor.block_id for anchor in anchors}
        return parse_decision(data, valid_block_ids=valid_block_ids, max_cards=self.config.max_cards)
