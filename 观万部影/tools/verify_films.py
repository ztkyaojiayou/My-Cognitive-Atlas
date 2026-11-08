#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
观万部影 · 全量校验

用法：
    python3 tools/verify_films.py            # 校验 films/ 下全部
    python3 tools/verify_films.py --strict   # 额外检查 04/05 段是否过短

检查项：
    1. 七段结构完整（01–07 标题逐字）
    2. 头部层级与《必看清单》一致（文明级 / 核心经典）
    3. 《自我探索》引用编号真实存在（X.Y 与 X.Y.Z 两种写法）
    4. 贯穿轴组号只允许 A–D
    5. 字符数落在层级区间（核心经典 4000–7000 / 文明级 5000–8000）
"""
import io
import os
import re
import sys
import glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILMS = os.path.join(BASE, 'films')
LIST = os.path.join(BASE, '观万部影-必看清单.md')

# 各小节的问题数量，用于校验 X.Y.Z 的 Z
QC = {
    '1.1': 12, '1.2': 10, '1.3': 10, '1.4': 10,
    '2.1': 10, '2.2': 10, '2.3': 10, '2.4': 10,
    '3.1': 10, '3.2': 10, '3.3': 10, '3.4': 10, '3.5': 10,
    '4.0': 6, '4.1': 11, '4.2': 11, '4.3': 10, '4.4': 10,
    '5.0': 6, '5.1': 12, '5.2': 15, '5.3': 12, '5.4': 12,
    '6.1': 12, '6.2': 10, '6.3': 10, '6.4': 10,
}
SECTIONS = ['## 01｜', '## 02｜', '## 03｜', '## 04｜', '## 05｜', '## 06｜', '## 07｜']


def load_tiers():
    """从必看清单读出哪些是文明级"""
    s = io.open(LIST, encoding='utf-8').read()
    civ = set()
    for line in s.splitlines():
        if re.match(r'^\| \d+ \|', line) and '文明级' in line:
            name = line.strip('|').split('|')[1]
            civ.add(re.split(r'[★🎬📽（(*]', name)[0].strip())
    return civ


def main():
    strict = '--strict' in sys.argv
    civ = load_tiers()
    files = sorted(glob.glob(os.path.join(FILMS, '*.md')))
    files = [f for f in files if '写作规范' not in f]

    problems = []
    total_chars = 0

    for f in files:
        s = io.open(f, encoding='utf-8').read()
        base = os.path.basename(f)
        total_chars += len(s)
        m = re.match(r'^# 《([^》]+)》', s)
        name = m.group(1) if m else '?'

        # 1 结构
        missing = [x for x in SECTIONS if x not in s]
        if missing:
            problems.append((base, '缺段 ' + ','.join(missing)))

        # 2 层级
        mt = re.search(r'清单[:：]\**\s*\S+\s*｜\s*(\S+)', s)
        tier = mt.group(1) if mt else '缺层级'
        if tier not in ('文明级', '核心经典'):
            problems.append((base, '层级字段异常：' + tier))
        elif (tier == '文明级') != (name in civ):
            problems.append((base, '层级与清单不一致：标 %s，应为 %s' %
                             (tier, '文明级' if name in civ else '核心经典')))

        # 3 引用编号
        for mm in re.finditer(r'(\d\.\d)(?:\.(\d+))?「', s):
            k, q = mm.group(1), mm.group(2)
            if k not in QC:
                problems.append((base, '无效节号 ' + k))
            elif q and int(q) > QC[k]:
                problems.append((base, '无效问题号 %s.%s' % (k, q)))

        # 4 贯穿轴组号
        for g in set(re.findall(r'贯穿轴\s*([A-Za-z])\s*组', s)):
            if g.upper() not in 'ABCD':
                problems.append((base, '无效组号 ' + g))

        # 5 字符区间
        lo, hi = (5000, 8000) if name in civ else (4000, 7000)
        if not (lo <= len(s) <= hi):
            problems.append((base, '字符 %d 超出 %d–%d' % (len(s), lo, hi)))

        if strict:
            seg = re.split(r'^## 0\d｜', s, flags=re.M)
            if len(seg) > 4 and len(seg[4]) < 1200:
                problems.append((base, '04 段偏短（%d 字符）' % len(seg[4])))
            if len(seg) > 5 and len(seg[5]) < 800:
                problems.append((base, '05 段偏短（%d 字符）' % len(seg[5])))

    print('校验文件数：%d   总字符：%d' % (len(files), total_chars))
    if not problems:
        print('✅ 全部通过')
        return
    cur = None
    for base, msg in problems:
        if base != cur:
            print('\n' + base)
            cur = base
        print('   • ' + msg)
    print('\n共 %d 个问题' % len(problems))


if __name__ == '__main__':
    main()
