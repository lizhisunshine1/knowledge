# 00_Inbox 知识库自动加工器

这个项目把原 `inbox-processor` 技能固化为可执行代码：除“是否入库、主题判断、思维导图/卡片内容提炼”交给本地大模型外，扫描、字符数判断、标题标识、文件移动、图片复制、Obsidian 链接、MOC、`index.md`、`log.md` 更新全部由 Python 精确执行。

## 运行前提

1. 当前目录是知识库根目录。
2. 本地 WPS Comate OpenAI 兼容代理已启动：

```powershell
python openai_proxy.py
```

3. 安装依赖：

```powershell
pip install -r requirements.txt
```

## 常用命令

仅查看待处理文件：

```powershell
python -m kb_inbox_processor --list
```

试运行，不写文件、不移动文件：

```powershell
python -m kb_inbox_processor --dry-run --limit 1
```

正式处理一篇：

```powershell
python -m kb_inbox_processor --limit 1
```

正式处理全部：

```powershell
python -m kb_inbox_processor
```

覆盖模型或代理地址：

```powershell
python -m kb_inbox_processor --model default --base-url http://localhost:8000/v1
```

## 处理规则

- 从 `00_Inbox/` 递归扫描 `.md` 文件，跳过 `README.md`。
- 按字符数降序处理，优先处理长文。
- 少于 `500` 字：不调用大模型，直接跳过；默认移入 `todelete/` 并保留原相对结构。
- 大于等于 `500` 字：由代码给每个 Markdown 标题或整行加粗标题追加 `^sX-Y`。
- 如果没有标题，则给第一行非空正文追加 `^s1-1`，保证思维导图有可定位来源。
- 将带标识原文发送给本地大模型，大模型只返回 JSON 决策和提炼结果。
- 入库时：
  - 原文进入对应主题 `inbox/`。
  - 有图片或其他资源时使用 `inbox/文章名/文章名.md + images/` 子目录隔离。
  - 无资源时平铺为 `inbox/文章名.md`。
  - 思维导图进入 `abstract/思维导图：文章名.md`。
  - 卡片进入对应卡片目录。
  - 思维导图单向链接到原文 block id。
  - 卡片与思维导图/原文建立双向链接。
  - 更新对应主题 MOC、根 `index.md` 和 `log.md`。

## 配置

默认配置在 `kb_processor_config.json`：

```json
{
  "min_chars": 500,
  "model": "default",
  "base_url": "http://localhost:8000/v1",
  "max_cards": 6,
  "short_action": "move",
  "keep_source": false
}
```

`short_action` 可设为 `keep`，让短文保持在 `00_Inbox` 原地不动。

`keep_source` 设为 `true` 时，入库成功后不清理 `00_Inbox` 源文件。

## 代码结构

- `kb_inbox_processor/scanner.py`：扫描 Inbox、字符数、标题去时间戳、安全文件名。
- `kb_inbox_processor/blocks.py`：精确添加与校验 `^sX-Y` 块标识。
- `kb_inbox_processor/llm.py`：唯一的大模型调用模块，使用 OpenAI 兼容本地代理。
- `kb_inbox_processor/render.py`：生成思维导图、卡片、Obsidian 链接。
- `kb_inbox_processor/fsops.py`：原子写入、复制图片、移动到 `todelete`、清理源文件。
- `kb_inbox_processor/indexing.py`：更新 MOC、`index.md` 自动块、`log.md`。
- `kb_inbox_processor/processor.py`：完整处理流水线。
- `kb_inbox_processor/cli.py`：命令行入口。

## 测试

```powershell
python -m unittest discover -s tests
```
