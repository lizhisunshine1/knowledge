from __future__ import annotations

import argparse
from pathlib import Path

from .config import ProcessorConfig
from .processor import process_inbox
from .scanner import scan_inbox


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process 00_Inbox into the Obsidian knowledge base.")
    parser.add_argument("--root", default=".", help="知识库根目录，默认当前目录")
    parser.add_argument("--config", default=None, help="配置文件路径，默认 kb_processor_config.json")
    parser.add_argument("--limit", type=int, default=None, help="最多处理多少篇")
    parser.add_argument("--dry-run", action="store_true", help="只展示将执行的动作，不写文件、不移动文件")
    parser.add_argument("--list", action="store_true", help="仅列出 00_Inbox 中待处理文件")
    parser.add_argument("--keep-source", action="store_true", help="入库成功后保留 00_Inbox 原文件")
    parser.add_argument("--model", default=None, help="覆盖模型名，默认 default")
    parser.add_argument("--base-url", default=None, help="覆盖 OpenAI 兼容代理地址")
    parser.add_argument("--api-key", default=None, help="覆盖 API key")
    parser.add_argument("--short-action", choices=["move", "keep"], default=None, help="短文跳过时 move 到 todelete 或 keep 原地保留")
    return parser


def _print_results(results, actions) -> None:
    if not results:
        print("Inbox 为空，无需处理。")
        return
    for result in results:
        print(f"[{result.status}] {result.item_title} - {result.reason}")
        if result.source_path:
            print(f"  原文: {result.source_path}")
        if result.mindmap_path:
            print(f"  思维导图: {result.mindmap_path}")
        if result.card_paths:
            print("  卡片:")
            for path in result.card_paths:
                print(f"    - {path}")
    if actions:
        print("\nDry-run actions:")
        for action in actions:
            print(f"  - {action}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    config_path = Path(args.config).resolve() if args.config else None
    config = ProcessorConfig.load(root, config_path)

    if args.model:
        config.model = args.model
    if args.base_url:
        config.base_url = args.base_url
    if args.api_key:
        config.api_key = args.api_key
    if args.keep_source:
        config.keep_source = True
    if args.short_action:
        config.short_action = args.short_action

    if args.list:
        items = scan_inbox(root, config)
        if not items:
            print("Inbox 为空。")
            return 0
        for item in items:
            print(f"{item.char_count:>7} chars | {item.relative_md_path} | title={item.title}")
        return 0

    results, actions = process_inbox(root, config, limit=args.limit, dry_run_enabled=args.dry_run)
    _print_results(results, actions)
    return 0 if all(result.status != "error" for result in results) else 1
