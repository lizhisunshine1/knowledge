"""
精确修复所有 ^sX-Y 块引用：
1. 将内嵌在段落中间的块引用移到段落末尾
2. 分离块ID和后面粘连的中文字符
3. 确保块ID在行末，后面无任何字符
"""
import re, os

files = {
    '平等的古巴': 'C:/lzj/成长/kownledge/03_Resources/01_底层原理/inbox/在平等的古巴，我重新理解了贫穷/在平等的古巴，我重新理解了贫穷.md',
    '别卷体力': 'C:/lzj/成长/kownledge/03_Resources/01_底层原理/inbox/别卷体力。真想卷，卷理解能力。/别卷体力。真想卷，卷理解能力。.md',
    '给管理者': 'C:/lzj/成长/kownledge/03_Resources/01_底层原理/inbox/给管理者的5点建议/给管理者的5点建议.md',
    '空调案例': 'C:/lzj/成长/kownledge/03_Resources/01_底层原理/inbox/空调，这个百年不变的老行业，正在被重新定义/空调，这个百年不变的老行业，正在被重新定义.md',
}

# 只匹配 ASCII 字符的块引用ID
pattern = re.compile(r'\^s[A-Za-z0-9_-]+')

for name, path in files.items():
    if not os.path.exists(path):
        print(f'❌ {name}: 文件不存在')
        continue

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 收集所有块引用 + 位置
    markers = []
    for m in pattern.finditer(content):
        bid = m.group()
        start = m.start()
        end = m.end()
        after = content[end:end+3]
        at_line_end = len(after.strip()) == 0 or after[0] in '\n\r'
        markers.append({
            'bid': bid,
            'start': start,
            'end': end,
            'at_line_end': at_line_end,
            'trailing_content': '' if at_line_end else after
        })

    # 先处理一个特殊情况：多个块引用挤在同一行末尾
    # 对每个块引用，找到它真正应该归属的段落末尾
    # 由于块引用被手工插入在各个段落中间，我们需要：
    # 1. 找到每个块引用对应的段落（通过段落内容判断）
    # 2. 将块引用移到该段落的末尾

    if not markers:
        print(f'⏭️ {name}: 无块引用')
        continue

    # 从后往前处理
    result = content
    modified = False

    # 按位置从后往前排序
    sorted_markers = sorted(markers, key=lambda x: -x['start'])

    for m in sorted_markers:
        bid = m['bid']
        start = m['start']
        end = m['end']
        at_line_end = m['at_line_end']

        if at_line_end:
            continue  # 已经是有效的

        # 在 result（可能已被之前的操作修改）中找到这个 bid
        # 从原始位置附近查找
        pos = result.find(bid)
        if pos == -1:
            # 可能已经被前面的处理移走了
            continue

        # 确认这是我们要找的那个（不是其他文本中的相同ID）
        # 用上下文做匹配
        # 简单处理：找最近的匹配

        # 提取块ID后的文本（中文内容，不是块ID的一部分）
        bid_end = pos + len(bid)
        trail_text = ''
        trail_end = bid_end
        while trail_end < len(result) and result[trail_end] not in '\n\r':
            trail_text += result[trail_end]
            trail_end += 1

        # 如果后面有空格，保留空格
        trailing_spaces = ''
        while trail_text and trail_text[0] in ' \t':
            trailing_spaces += trail_text[0]
            trail_text = trail_text[1:]
            trail_end_adj = bid_end + len(trailing_spaces)
        else:
            trail_end_adj = bid_end

        # 找到段落末尾（下一个空行或文件末尾）
        para_end = result.find('\n\n', trail_end)
        if para_end == -1:
            para_end = len(result)

        # 删除块引用（但不删除后续的中文内容）
        # 注意：trail_text 是中文内容，应该保留在原位
        result = result[:pos] + trailing_spaces + trail_text + result[trail_end:]

        # 调整 para_end 偏移
        deletion_len = trail_end - pos - len(trail_text) - len(trailing_spaces)
        if para_end > pos:
            para_end_adj = para_end - deletion_len
        else:
            para_end_adj = para_end

        # 在段落末尾插入块引用
        insert_text = f' {bid}'
        result = result[:para_end_adj] + insert_text + result[para_end_adj:]

        modified = True

    if modified and result != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(result)

        # 验证
        valid, invalid = 0, 0
        for mm in pattern.finditer(result):
            b = mm.group()
            rest = result[mm.end():mm.end()+3]
            if not rest or rest[0] in '\n\r':
                valid += 1
            else:
                invalid += 1
                ctx = result[mm.end():mm.end()+10].replace('\n','↵')
                print(f'  ⚠️  {b} 仍无效: 后面"{ctx}"')

        print(f'✅ {name}: 修复完成 | {valid}有效/{invalid}无效')
    else:
        print(f'⏭️ {name}: 无需修改 ({len(markers)}个块引用均已有效)')