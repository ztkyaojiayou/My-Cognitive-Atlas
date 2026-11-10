#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通识指南 · 卡片全量校验

用法：
    python3 tools/verify_cards.py
    python3 tools/verify_cards.py --strict   # 额外检查"硬事实是否出现在事实基线中"

检查项：
    1. 每张卡片八段结构齐全（一句话理解 + 一至七）
    2. 字数落在层级区间（L1 800–1000 / L2 1000–1300 / L3 1300–1500，容差 ±250）
    3. 卡片的模块归属与所在目录一致
    4. 每个一级模块有「导读.md」，有卡片的模块有「事实基线.md」
    5. --strict：卡片中的年份/数字，是否能在该模块 事实基线.md 中找到
"""
import io
import os
import re
import sys
import glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 卡片八段（一句话理解 + 一至七）
SECTIONS = ['## 一句话理解', '## 一、', '## 二、', '## 三、', '## 四、', '## 五、', '## 六、', '## 七、']

# 层级字数区间：按**汉字数**计（与卡片模板的「字」一致），含容差
RANGE = {'L1': (700, 1150), 'L2': (850, 1400), 'L3': (1050, 1700)}


def module_dirs():
    out = []
    for d in sorted(glob.glob(os.path.join(BASE, '[0-9][0-9]-*'))):
        if os.path.isdir(d):
            out.append(d)
    return out


def check_card(path):
    """返回问题列表"""
    probs = []
    s = io.open(path, encoding='utf-8').read()
    base = os.path.basename(path)
    mod = os.path.basename(os.path.dirname(os.path.dirname(path)))

    # 1 结构
    missing = [x for x in SECTIONS if x not in s]
    if missing:
        probs.append('缺段: ' + ' / '.join(m.rstrip('、') for m in missing))

    # 2 字数
    m = re.search(r'层级[：:]\s*\**\s*(L[123])', s)
    lvl = m.group(1) if m else None
    if not lvl:
        probs.append('未标层级（头部应有「层级：L1/L2/L3」）')
    else:
        han = len(re.findall(r'[\u4e00-\u9fff]', s))
        lo, hi = RANGE[lvl]
        if not (lo <= han <= hi):
            probs.append('汉字数 %d 超出 %s 区间 %d–%d' % (han, lvl, lo, hi))

    # 3 模块归属
    mm = re.search(r'模块[：:]\s*\**\s*(\d{2})-', s)
    if mm:
        num = mm.group(1)
        if not mod.startswith(num + '-'):
            probs.append('模块号 %s 与所在目录 %s 不一致' % (num, mod))
    else:
        probs.append('头部缺「模块：NN-模块名」')

    # 4 strict：硬事实是否在事实基线里
    if '--strict' in sys.argv:
        bl = os.path.join(os.path.dirname(os.path.dirname(path)), '事实基线.md')
        if not os.path.exists(bl):
            probs.append('缺事实基线.md，无法核对硬事实')
        else:
            facts = io.open(bl, encoding='utf-8').read()
            body = re.sub(r'^>.*$', '', s, flags=re.M)  # 去掉头部引用块（含更新日期）
            nums = set(re.findall(r'\b(1[6-9]\d{2}|20\d{2})\b', body))  # 年份
            miss = [n for n in nums if n not in facts]
            if miss:
                probs.append('年份未见于事实基线: ' + ','.join(sorted(miss)[:8]))
    return probs


def main():
    mods = module_dirs()
    if not mods:
        print('未找到模块目录（应形如 20-法律与法治/）')
        return

    problems = []
    cards = sorted(glob.glob(os.path.join(BASE, '[0-9][0-9]-*', 'cards', '*.md')))

    for d in mods:
        name = os.path.basename(d)
        if not os.path.exists(os.path.join(d, '导读.md')):
            problems.append((name, '缺 导读.md'))
        own = glob.glob(os.path.join(d, 'cards', '*.md'))
        if own and not os.path.exists(os.path.join(d, '事实基线.md')):
            problems.append((name, '有卡片但缺 事实基线.md'))

    for c in cards:
        for p in check_card(c):
            problems.append((os.path.relpath(c, BASE), p))

    print('模块 %d 个，卡片 %d 张' % (len(mods), len(cards)))
    if not problems:
        print('✅ 全部通过')
        return
    cur = None
    for name, msg in problems:
        if name != cur:
            print('\n' + name)
            cur = name
        print('   • ' + msg)
    print('\n共 %d 个问题' % len(problems))


if __name__ == '__main__':
    main()
