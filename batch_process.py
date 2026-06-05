#!/usr/bin/env python3
"""批量处理00_Inbox中的10篇文章：加标识+复制入库"""
import os, shutil, re

INBOX = "00_Inbox"
BASE = "03_Resources"

articles = [
    ('20260208101639_长期主义，是强者的胜利。', '长期主义是强者的胜利', '01_底层原理', [
        ('长期主义的另一种解法', '^s1-1'),
        ('当下主义×最小闭环', '^s1-2'),
        ('当下主义×顺势而为', '^s1-3'),
    ]),
    ('20260210151622_2026，会是传统电影的\u201c最后一年\u201d吗？', '传统电影最后一年', '03_AI与计算机', [
        ('改变视频行业的AI', '^s1-1'),
        ('两只手画画', '^s1-2'),
        ('用本人授权', '^s1-3'),
    ]),
    ('20260210151622_所有的合作，都应该创造全局增量：如何做一名优秀的商务？', '全局增量合作', '01_底层原理', [
        ('理解对方', '^s1-1'),
        ('了解自己', '^s1-2'),
        ('专业知识', '^s1-3'),
        ('卖流量', '^s1-4'),
        ('信用', '^s1-5'),
    ]),
    ('20260210212133_刘润：预制菜这件事，还有救吗？', '预制菜还有救吗', '01_底层原理', [
        ('预制菜', '^s1-1'),
    ]),
    ('20260210222614_\u201c库存无法过夜\u201d的生意，都是在和时间赛跑', '库存无法过夜', '01_底层原理', [
        ('库存无法过夜', '^s1-1'),
        ('拆解你的生意', '^s1-2'),
        ('降价', '^s1-3'),
        ('分类', '^s1-4'),
        ('提效', '^s1-5'),
    ]),
    ('20260210222614_如何高效学习？', '如何高效学习', '01_底层原理', [
        ('认知之树', '^s1-1'),
        ('须鲸式学习', '^s1-2'),
        ('大量输入', '^s1-3'),
    ]),
    ('20260211230501_库迪咖啡为什么\u201c背叛\u201d了9.9？', '库迪咖啡背叛9.9', '01_底层原理', [
        ('日盈亏线', '^s1-1'),
        ('利益错位', '^s1-2'),
        ('供应链差价', '^s1-3'),
    ]),
    ('20260211230501_谈判的本质，是让对手获胜，让自己获益', '谈判的本质', '01_底层原理', [
        ('把对方当合作者', '^s1-1'),
        ('关注自己得分', '^s1-2'),
        ('投桃报李', '^s1-3'),
        ('对立的面', '^s1-4'),
    ]),
    ('20260209094045_一定要读的35本商业书 _ 年度书单', '35本商业书', '01_底层原理', [
        ('经济学', '^s1-1'),
        ('管理学', '^s1-2'),
        ('战略', '^s1-3'),
        ('营销', '^s1-4'),
        ('金融', '^s1-5'),
        ('创新', '^s1-6'),
        ('个人习惯', '^s1-7'),
    ]),
    ('20260209094045_刘润对话樊登：读书，几乎是唯一有用的事情', '刘润对话樊登', '01_底层原理', [
        ('语言的遮蔽性', '^s1-1'),
        ('人不能学习经验', '^s1-2'),
        ('读书，几乎是唯一有用', '^s1-3'),
    ]),
]

results = []

for src_dir, short_title, topic, block_ids in articles:
    src_path = os.path.join(INBOX, src_dir)
    if not os.path.isdir(src_path):
        results.append(f'SKIP {short_title}: 源目录不存在')
        continue

    md_files = [f for f in os.listdir(src_path) if f.endswith('.md')]
    if not md_files:
        results.append(f'SKIP {short_title}: 无md文件')
        continue

    src_md = os.path.join(src_path, md_files[0])

    with open(src_md, 'r', encoding='utf-8') as f:
        content = f.read()

    # 加块标识
    modified = content
    added = 0
    for keyword, block_id in block_ids:
        lines = modified.split('\n')
        new_lines = []
        for line in lines:
            if keyword in line and block_id not in line:
                stripped = line.rstrip()
                if stripped.endswith('**'):
                    prefix = stripped[:-2].rstrip()
                    new_lines.append(prefix + ' ' + block_id)
                else:
                    new_lines.append(stripped + ' ' + block_id)
                added += 1
            else:
                new_lines.append(line)
        modified = '\n'.join(new_lines)

    # 确保标识后有空行
    final_lines = modified.split('\n')
    i = 0
    while i < len(final_lines):
        line = final_lines[i]
        for _, bid in block_ids:
            if bid in line and line.rstrip().endswith(bid):
                if i+1 < len(final_lines) and final_lines[i+1].strip() != '':
                    final_lines.insert(i+1, '')
                    break
        i += 1
    modified = '\n'.join(final_lines)

    # 复制到目标inbox
    target_inbox = os.path.join(BASE, topic, 'inbox', short_title)
    os.makedirs(target_inbox, exist_ok=True)
    target_md = os.path.join(target_inbox, f'{short_title}.md')
    with open(target_md, 'w', encoding='utf-8') as f:
        f.write(modified)

    # 复制images/
    src_images = os.path.join(src_path, 'images')
    if os.path.isdir(src_images):
        dst_images = os.path.join(target_inbox, 'images')
        if os.path.exists(dst_images):
            shutil.rmtree(dst_images)
        shutil.copytree(src_images, dst_images)

    # 验证
    with open(target_md, 'r', encoding='utf-8') as f:
        target_content = f.read()
    valid = 0
    for _, bid in block_ids:
        pattern = re.escape(bid) + r'(?:\s*$)'
        if re.search(pattern, target_content, re.MULTILINE):
            valid += 1

    status = 'OK' if valid == len(block_ids) else f'PARTIAL'
    results.append(f'{status} {short_title}: {valid}/{len(block_ids)} 标识有效 -> {topic}')

for r in results:
    print(r)

ok_count = sum(1 for r in results if r.startswith('OK'))
partial_count = sum(1 for r in results if r.startswith('PARTIAL'))
skip_count = sum(1 for r in results if r.startswith('SKIP'))
print(f'\n总计: {ok_count}篇完全成功, {partial_count}篇部分成功, {skip_count}篇跳过')
