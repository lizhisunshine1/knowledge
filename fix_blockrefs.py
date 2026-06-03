import re, os

articles = [
    ('平等的古巴', 'C:/lzj/成长/kownledge/03_Resources/01_底层原理/inbox/在平等的古巴，我重新理解了贫穷/在平等的古巴，我重新理解了贫穷.md'),
    ('别卷体力', 'C:/lzj/成长/kownledge/03_Resources/01_底层原理/inbox/别卷体力。真想卷，卷理解能力。/别卷体力。真想卷，卷理解能力。.md'),
    ('给管理者', 'C:/lzj/成长/kownledge/03_Resources/01_底层原理/inbox/给管理者的5点建议/给管理者的5点建议.md'),
    ('空调案例', 'C:/lzj/成长/kownledge/03_Resources/01_底层原理/inbox/空调，这个百年不变的老行业，正在被重新定义/空调，这个百年不变的老行业，正在被重新定义.md'),
]

pattern = re.compile(r'\^s[\w-]+')

for name, path in articles:
    if not os.path.exists(path):
        print(f'❌ {name}: 文件不存在')
        continue
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 收集所有需要修复的块引用: (bid, start, end)
    # 从后往前扫描处理
    invalid_markers = []
    for m in pattern.finditer(content):
        bid = m.group()
        end = m.end()
        # 如果后面有非空白/换行字符，则需要修复
        rest = content[end:end+3]
        if rest and not rest[0] in '\n\r':
            invalid_markers.append((bid, m.start(), end))
    
    if not invalid_markers:
        print(f'⏭️ {name}: 无需修复')
        continue
    
    # 从后往前处理
    chars = list(content)
    for bid, start, end in reversed(invalid_markers):
        # 计算要删除的终点：从 ^sX-Y 后到第一个换行为止
        delete_end = end
        while delete_end < len(chars) and chars[delete_end] not in '\n\r':
            delete_end += 1
        
        # 找到段落真正的末尾（下一个空行 \n\n 或文件末尾）
        # 从 delete_end 位置开始找
        para_end = content.find('\n\n', delete_end)
        if para_end == -1:
            para_end = len(content)
        
        # 计算在 chars 中的调整后位置
        # 已处理的删除会改变位置的偏移
        # 简化：直接在原始字符串上做
        pass
    
    # 用字符串替换方式，从后往前处理更安全
    result = content
    processed = 0
    for bid, start, end in sorted(invalid_markers, key=lambda x: -x[1]):
        # 在 result 中找到当前 bid 的位置
        pos = result.rfind(bid, 0, end + 50)
        if pos == -1:
            continue
        
        # 计算删除终点（到行末）
        del_end = pos + len(bid)
        while del_end < len(result) and result[del_end] not in '\n\r':
            del_end += 1
        
        # 找到段落末尾（下一个空行或文件末尾）
        para_end = result.find('\n\n', del_end)
        if para_end == -1:
            para_end = len(result)
        
        # 从字符串中删除 block-ref 和后面的字符
        result = result[:pos] + result[del_end:]
        
        # 调整 para_end（因为删除了字符）
        if para_end > pos:
            para_end_adj = para_end - (del_end - pos)
        else:
            para_end_adj = para_end
        
        # 在段落末尾插入 block-ref
        insert_text = f' {bid}'
        result = result[:para_end_adj] + insert_text + result[para_end_adj:]
        
        processed += 1
    
    if result != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(result)
        
        # 验证
        new_valid = 0
        new_invalid = 0
        for m in pattern.finditer(result):
            bid = m.group()
            rest = result[m.end():m.end()+3]
            if not rest or rest[0] in '\n\r':
                new_valid += 1
            else:
                new_invalid += 1
        
        print(f'✅ {name}: 修复 {processed} 处 | 验证: {new_valid} 有效 / {new_invalid} 无效')
    else:
        print(f'⏭️ {name}: 内容未变化')
