#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆瓣 Top250 × 观万部影必看清单 —— 交叉核对工具

用法：
    python3 tools/douban_compare.py             # 只比对，打印结果
    python3 tools/douban_compare.py --rebuild   # 比对并重新生成对照表

适用场景：
    豆瓣榜单每年小幅调整。把新版榜单文件放进 观万部影/ 目录（文件名含"豆瓣"和".md"），
    跑一次本脚本，即可看出：哪些新片进了榜、哪些掉了、我清单里的片子名次怎么动。

约定：
    - 榜单文件：观万部影/ 下文件名包含 "豆瓣" 且以 .md 结尾的最新一份
    - 清单文件：观万部影/观万部影-必看清单.md
    - 对照表：  观万部影/豆瓣Top250-对照表.md
"""
import io
import os
import re
import sys
import glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST_FILE = os.path.join(BASE, '观万部影-必看清单.md')
TABLE_FILE = os.path.join(BASE, '豆瓣Top250-对照表.md')

# ── 明确不进的片目（分类理由见 CLASSIFY） ─────────────────────────────
SERIES = [
    '哈利·波特与魔法石', '哈利·波特与密室', '哈利·波特与阿兹卡班的囚徒',
    '哈利·波特与火焰杯', '哈利·波特与凤凰社', '哈利·波特与死亡圣器(上)',
    '哈利·波特与死亡圣器(下)', '指环王1：护戒使者', '指环王2：双塔奇兵',
    '指环王3：王者无敌', '教父2', '教父3', '蝙蝠侠：黑暗骑士崛起',
    '黑客帝国2：重装上阵', '黑客帝国3：矩阵革命', '无间道2',
    '谍影重重', '谍影重重2', '谍影重重3', '终结者2：审判日',
    '小森林 夏秋篇', '小森林 冬春篇',
]
ANIM = ['玩具总动员3', '怪兽电力公司', '神偷奶爸', '疯狂原始人', '冰川时代',
        '无敌破坏王', '冰雪奇缘', '超能陆战队']
EMO = ['忠犬八公的故事', '忠犬八公物语', '怦然心动', '海蒂和爷爷', '菊次郎的夏天',
       '借东西的小人阿莉埃蒂', '7号房的礼物', '飞屋环游记', '崖上的波妞',
       '魔女宅急便', '侧耳倾听', '萤火之森', '你看起来好像很好吃',
       '初恋这件小事', '恋恋笔记本', '真爱至上', '花束般的恋爱', '狮子王',
       '唐伯虎点秋香', '喜剧之王', '大闹天宫', '天书奇谭', '哪吒闹海',
       '九品芝麻官', '射雕英雄传之东成西就']
ENT = ['猫鼠游戏', '看不见的客人', '致命ID', '致命魔术', '禁闭岛', '蝴蝶效应',
       '两杆大烟枪', '源代码', '头号玩家', '恐怖游轮', '彗星来的那一夜', '电锯惊魂']

REASONS = [
    (SERIES, '系列/续集：代表作已收，其余不占名额'),
    (ANIM, '商业动画：认知密度低，主题已被收入动画覆盖'),
    (EMO, '情绪/治愈向：好看，但认知密度低'),
    (ENT, '类型娱乐：主题已由收入作品覆盖'),
]


def clean(s):
    return s.replace('\\', '').strip()


def norm(s):
    """片名规范化：截断到第一个标记符，只保留汉字/字母/数字"""
    s = re.split(r'[★🎬📽（(*]', s)[0]
    return re.sub(r'[^一-龥A-Za-z0-9]', '', s).lower()


def find_douban_file():
    files = [f for f in glob.glob(os.path.join(BASE, '*.md')) if '豆瓣' in os.path.basename(f)]
    files = [f for f in files if '对照表' not in os.path.basename(f)]
    if not files:
        sys.exit('找不到豆瓣榜单文件（文件名需包含"豆瓣"且以 .md 结尾）')
    return max(files, key=os.path.getmtime)


def parse_douban(path):
    films = []
    for line in io.open(path, encoding='utf-8'):
        if re.match(r'^\|\d+\|', line):
            c = line.strip('|').split('|')
            name = clean(c[1].split('<br>')[0].replace('**', ''))
            y = re.search(r'(\d{4})', c[3])
            films.append(dict(
                rank=int(c[0]), name=name,
                year=y.group(1) if y else '?',
                region=clean(c[3].split('<br>')[-1]),
                rating=clean(c[5]) if len(c) > 5 else '',
            ))
    return films


def parse_list(path):
    names = []
    for line in io.open(path, encoding='utf-8'):
        if re.match(r'^\| \d+ \|', line):
            names.append(line.strip('|').split('|')[1].strip())
    return names


def parse_old_table(path):
    """读取已有对照表 → {片名: 排名}"""
    if not os.path.exists(path):
        return {}
    old = {}
    for line in io.open(path, encoding='utf-8'):
        m = re.match(r'^\| (\d+) \| ([^|]+) \|', line)
        if m:
            old[clean(m.group(2))] = int(m.group(1))
    return old


def classify(name, mine_set):
    if norm(name) in mine_set:
        return '✅ 已收', ''
    for names, why in REASONS:
        if name in names:
            return '❌ 不进', why
    return '⏸ 留待 Level 2', ''


def main():
    rebuild = '--rebuild' in sys.argv
    db_path = find_douban_file()
    films = parse_douban(db_path)
    mine = parse_list(LIST_FILE)
    mine_set = {norm(n) for n in mine}

    print(f'榜单：{os.path.basename(db_path)}（{len(films)} 部）')
    print(f'清单：{len(mine)} 部')

    # 与旧对照表比对
    old = parse_old_table(TABLE_FILE)
    if old:
        new_in = [f['name'] for f in films if f['name'] not in old]
        dropped = [n for n in old if n not in {f['name'] for f in films}]
        moved = []
        for f in films:
            if f['name'] in old and old[f['name']] != f['rank']:
                moved.append((f['name'], old[f['name']], f['rank']))
        print(f'\n相对上一版对照表：新入榜 {len(new_in)} 部，掉出 {len(dropped)} 部，名次变动 {len(moved)} 部')
        for n in new_in[:20]:
            print(f'  + {n}')
        for n in dropped[:20]:
            print(f'  - {n}')
        for n, a, b in sorted(moved, key=lambda x: x[1] - x[2])[:10]:
            print(f'  ↑ {n}: {a} → {b}')

    cnt = {'✅ 已收': 0, '❌ 不进': 0, '⏸ 留待 Level 2': 0}
    rows = []
    for f in films:
        st, why = classify(f['name'], mine_set)
        cnt[st] += 1
        rows.append((f['rank'], f['name'], f['year'], f['region'], f['rating'], st, why))

    print(f'\n账目：已收 {cnt["✅ 已收"]} · 留待 L2 {cnt["⏸ 留待 Level 2"]} · 不进 {cnt["❌ 不进"]}')

    # 清单里有、但不在豆瓣榜的
    db_set = {norm(f['name']) for f in films}
    not_in_db = [n for n in mine if norm(n) not in db_set]
    print(f'清单中不在豆瓣 Top250 的：{len(not_in_db)} 部（影史/艺术/纪录片层，属正常）')

    if not rebuild:
        print('\n（加 --rebuild 可重新生成对照表）')
        return

    out = ['# 豆瓣 Top 250 · 对照表（自动生成）\n',
           f'> 基准：`{os.path.basename(db_path)}`',
           f'> 对照：`观万部影-必看清单.md`（{len(mine)} 部）',
           '> 生成方式：`tools/douban_compare.py --rebuild`\n',
           '## 账目\n',
           '| 状态 | 数量 | 含义 |', '|---|---|---|',
           f'| ✅ 已收 | {cnt["✅ 已收"]} | 已进必看清单 |',
           f'| ⏸ 留待 Level 2 | {cnt["⏸ 留待 Level 2"]} | 有认知价值，但不必抢 125 的名额；是「200 部重要经典」的原料 |',
           f'| ❌ 不进 | {cnt["❌ 不进"]} | 明确不收，附理由 |',
           f'| **合计** | **{len(films)}** | |\n',
           '> **为什么不为了"覆盖榜单"而硬塞：** 豆瓣偏欧美、偏近三十年、偏情绪浓度。',
           '> 必看清单是"认知必看"，不是"热门必看"——差异是设计出来的，不是漏出来的。\n',
           '---\n', '## 全量对照（按豆瓣排名）\n',
           '| 排名 | 片名 | 年份 | 地区 | 评分 | 状态 | 理由 |',
           '|---|---|---|---|---|---|---|']
    for rank, name, year, region, rating, st, why in rows:
        out.append(f'| {rank} | {name} | {year} | {region} | {rating} | {st} | {why} |')
    io.open(TABLE_FILE, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print(f'已重新生成：{os.path.basename(TABLE_FILE)}')


if __name__ == '__main__':
    main()
