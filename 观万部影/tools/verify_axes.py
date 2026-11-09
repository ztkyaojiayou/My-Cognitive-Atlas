#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
观万部影 · 三条辅轴校验

用法：
    python3 tools/verify_axes.py

检查项：
    1. 三个辅轴入口存在：电影史/电影史-时间轴.md、世界电影/世界电影-国别地图.md、导演/README.md
    2. 电影史：十段结构齐全（## 一、… ## 十、），每段四块齐全
    3. 世界电影：十二区 + 短节齐全
    4. 导演：索引列 16 位，每位一个文件，六段齐全；影史导演总表 ≥120 位、按时代分节、时代内按国别分组
    5. 所有 ../films/xxx.md 链接真实存在
    6. 字符数落在约定区间
"""
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TIMELINE = os.path.join(BASE, '电影史', '电影史-时间轴.md')
WORLD = os.path.join(BASE, '世界电影', '世界电影-国别地图.md')
DIR_INDEX = os.path.join(BASE, '导演', 'README.md')
DIR_DIR = os.path.join(BASE, '导演')
DIR_TOTAL = os.path.join(BASE, '导演', '影史导演总表.md')

CN_NUM = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']

problems = []


def read(path):
    if not os.path.exists(path):
        problems.append((os.path.relpath(path, BASE), '文件不存在'))
        return ''
    return io.open(path, encoding='utf-8').read()


def check_links(path, text):
    """校验 Markdown 里 ../films/xxx.md 相对链接真实存在"""
    base = os.path.dirname(path)
    for target in sorted(set(re.findall(r'\]\(\.\./films/([^)]+\.md)\)', text))):
        full = os.path.normpath(os.path.join(base, '..', 'films', target))
        if not os.path.exists(full):
            problems.append((os.path.relpath(path, BASE), '链接缺失：films/' + target))
    # 反向链接（辅轴之间）
    for target in sorted(set(re.findall(r'\]\(\.\./(电影史|世界电影|导演)/([^)]+\.md)\)', text))):
        full = os.path.normpath(os.path.join(base, '..', target[0], target[1]))
        if not os.path.exists(full):
            problems.append((os.path.relpath(path, BASE), '链接缺失：%s/%s' % target))


def check_timeline():
    s = read(TIMELINE)
    if not s:
        return
    if not (5000 <= len(s) <= 10000):
        problems.append(('电影史/电影史-时间轴.md', '字符 %d 超出 5000–10000' % len(s)))
    for n in CN_NUM[:10]:
        if ('## %s、' % n) not in s:
            problems.append(('电影史/电影史-时间轴.md', '缺时代段落：' + n))
    for label in ('### 时代问题', '### 技术与工业', '### 代表片目', '### 留下什么'):
        cnt = s.count(label)
        if cnt < 10:
            problems.append(('电影史/电影史-时间轴.md', '%s 只有 %d 处（应 ≥10）' % (label, cnt)))
    check_links(TIMELINE, s)


def check_world():
    s = read(WORLD)
    if not s:
        return
    if not (5000 <= len(s) <= 13000):
        problems.append(('世界电影/世界电影-国别地图.md', '字符 %d 超出 5000–13000' % len(s)))
    for n in CN_NUM[:12]:
        if ('## %s、' % n) not in s:
            problems.append(('世界电影/世界电影-国别地图.md', '缺地区段落：' + n))
    if '## 短节：拉美与非洲' not in s:
        problems.append(('世界电影/世界电影-国别地图.md', '缺短节：拉美与非洲'))
    blocks = re.findall(r'^### 类型特长', s, re.M)
    if len(blocks) != 12:
        problems.append(('世界电影/世界电影-国别地图.md', '类型特长块 %d 个（应为 12）' % len(blocks)))
    stubs = re.findall(r'^\*\*片单外的招牌\*\*', s, re.M)
    if len(stubs) != 13:
        problems.append(('世界电影/世界电影-国别地图.md', '片单外招牌 %d 处（应为 12 区 + 短节 = 13）' % len(stubs)))
    check_links(WORLD, s)


def check_directors():
    index = read(DIR_INDEX)
    if not index:
        return
    rows = re.findall(r'^\| \d+ \|', index, re.M)
    if len(rows) != 16:
        problems.append(('导演/README.md', '索引行数 %d（应为 16）' % len(rows)))

    files = sorted(f for f in os.listdir(DIR_DIR) if f.startswith('导演-') and f.endswith('.md'))
    if len(files) != 16:
        problems.append(('导演/', '导演档案 %d 个（应为 16）' % len(files)))

    for f in files:
        p = os.path.join(DIR_DIR, f)
        s = io.open(p, encoding='utf-8').read()
        rel = '导演/' + f
        if not (600 <= len(s) <= 1600):
            problems.append((rel, '字符 %d 超出 600–1600' % len(s)))
        for n in CN_NUM[:6]:
            if ('## %s、' % n) not in s:
                problems.append((rel, '缺段落：' + n))
        check_links(p, s)

    for target in sorted(set(re.findall(r'\]\((导演-[^)]+\.md)\)', index))):
        if not os.path.exists(os.path.join(DIR_DIR, target)):
            problems.append(('导演/README.md', '索引链接缺失：' + target))


def check_total():
    s = read(DIR_TOTAL)
    if not s:
        return
    rows = [l for l in s.splitlines()
            if l.startswith('| ') and '---' not in l and not l.startswith('| 导演')]
    if len(rows) < 120:
        problems.append(('导演/影史导演总表.md', '导演行数 %d（应 ≥120）' % len(rows)))
    eras = re.findall(r'^## [一二三四五六七八九十]+、', s, re.M)
    if len(eras) < 5:
        problems.append(('导演/影史导演总表.md', '时代分节只有 %d 段（应 ≥5）' % len(eras)))
    groups = re.findall(r'^### ', s, re.M)
    if len(groups) < 30:
        problems.append(('导演/影史导演总表.md', '国别分组只有 %d 个（应 ≥30）' % len(groups)))
    for target in sorted(set(re.findall(r'\]\((导演-[^)]+\.md)\)', s))):
        if not os.path.exists(os.path.join(DIR_DIR, target)):
            problems.append(('导演/影史导演总表.md', '画像链接缺失：' + target))
    check_links(DIR_TOTAL, s)


def main():
    check_timeline()
    check_world()
    check_directors()
    check_total()

    if not problems:
        print('✅ 三条辅轴全部通过')
        return
    cur = None
    for name, msg in problems:
        if name != cur:
            print('\n' + name)
            cur = name
        print('   • ' + msg)
    print('\n共 %d 个问题' % len(problems))
    sys.exit(1)


if __name__ == '__main__':
    main()
