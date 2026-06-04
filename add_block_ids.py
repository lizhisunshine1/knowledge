"""
将 ^sX-Y 块引用标识精确添加到原文段落末尾。
不修改任何原文内容，仅在段落/标题行末添加标识。
"""
import re, sys

def add_block_ids(filepath, mappings):
    """
    在原文精确位置添加 ^sX-Y 块引用标识。
    
    mappings: [(anchor_text, block_id), ...]
    - anchor_text: 段落/标题中唯一可匹配的文本片段
    - block_id: 要添加的标识，如 '^s1-1'
    
    规则：
    1. 在 anchor_text 所在行的末尾添加 ' ^sX-Y'
    2. 确保 ^sX-Y 后面没有任何字符（直接换行）
    3. 不修改任何原文内容
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 从后往前处理，避免位置偏移
    for anchor_text, block_id in sorted(mappings, key=lambda x: -content.find(x[0])):
        pos = content.find(anchor_text)
        if pos == -1:
            print(f'⚠️ 未找到锚点: "{anchor_text[:30]}..."')
            continue
        
        # 找到该行的末尾
        line_end = content.find('\n', pos)
        if line_end == -1:
            line_end = len(content)
        
        # 检查行末是否已有其他 ^s 标识
        line_before = content[pos:line_end]
        if re.search(r'\^s[A-Za-z0-9_-]+', line_before):
            print(f'⚠️ 该行已有块引用，跳过: "{anchor_text[:20]}..."')
            continue
        
        # 清除行尾多余空格
        while line_end > pos and content[line_end-1] in ' \t':
            line_end -= 1
        
        # 插入 block_id
        insert = f' {block_id}'
        content = content[:line_end] + insert + content[line_end:]
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'✅ 完成: {filepath}')
        return True
    else:
        print(f'⏭️ 无需修改: {filepath}')
        return False


def validate_block_ids(filepath):
    """验证所有 ^s 块引用是否都在行末，后面无字符"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = re.compile(r'\^s[A-Za-z0-9_-]+')
    valid = 0
    invalid = 0
    
    for m in pattern.finditer(content):
        rest = content[m.end():m.end()+3]
        if not rest or rest[0] in '\n\r':
            valid += 1
        else:
            invalid += 1
            after = content[m.end():m.end()+15].replace('\n','↵')
            print(f'  ❌ {m.group()} → 后面有字符: "{after}"')
    
    print(f'  块引用: {valid} 有效 / {invalid if invalid else 0} 无效')
    return invalid == 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python add_block_ids.py <文件路径>')
        sys.exit(1)
    
    filepath = sys.argv[1]
    print(f'\n📄 处理文件: {filepath}')
    
    # 这里需要用户手动编写 mappings
    # 示例：
    # mappings = [
    #     ("不可替代的段落开头文本", "^s1-1"),
    # ]
    
    print('请在脚本中定义 mappings 后运行')
