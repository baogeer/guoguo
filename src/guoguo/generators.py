"""题库生成：枚举各类型练习题。"""

import random

from .core import MIN_NUM


def add_sub_items(max_num):
    """
    枚举所有加减法题目，返回 [(key, text), ...]。
    key 按交换律归一化，用于相邻去重；text 保留原始顺序。
    """
    items = {}

    def put(op, a, b):
        if op == '+':
            key = ('+', min(a, b), max(a, b))
            text = f"{a} + {b} = "
        else:
            key = ('-', a, b)
            text = f"{a} - {b} = "
        items.setdefault(key, []).append(text)

    if max_num < MIN_NUM * 2:
        for a in range(0, max_num + 1):
            for b in range(0, max_num - a + 1):
                put('+', a, b)
            for b in range(0, a + 1):
                put('-', a, b)
    else:
        for a in range(MIN_NUM, max_num - MIN_NUM + 1):
            for b in range(MIN_NUM, max_num - a + 1):
                put('+', a, b)
        for a in range(MIN_NUM * 2, max_num + 1):
            for b in range(MIN_NUM, a - MIN_NUM + 1):
                put('-', a, b)

    return [(key, text) for key, texts in items.items() for text in texts]


def compare_expr_items(max_num, pool_size=200):
    """
    比大小：左右各是一个两步算式，如 3 + 3 ◯ 3 + 2。
    约束：每边的中间结果都在 [0, max_num]，两边得数不相等。
    返回 [(key, (expr_left, expr_right)), ...]，
    其中 expr = (a, op, b, value)。
    """
    exprs = []
    for a in range(1, max_num + 1):
        for b in range(1, max_num + 1):
            if a + b <= max_num:
                exprs.append((a, '+', b, a + b))
            if a - b >= 0:
                exprs.append((a, '-', b, a - b))

    if not exprs:
        return []

    # 算式集合过大时（max_num 很大）抽样，避免左右配对数量爆炸
    if len(exprs) > pool_size:
        exprs = random.sample(exprs, pool_size)

    items = []
    seen = set()
    for left in exprs:
        for right in exprs:
            if left[3] == right[3]:
                continue
            key = (left, right)
            if key in seen:
                continue
            seen.add(key)
            items.append((key, (left, right)))
    return items


def adjacent_items(max_num):
    """生成相邻数题库：两边挖空 + 中间挖空。"""
    items = []
    for i in range(1, max_num + 1):
        items.append((('sides', i), 1, i, None))
    for i in range(2, max_num):
        items.append((('mid', i - 1, i + 1), 2, i - 1, i + 1))
    return items


def blank_fill_items(max_num):
    """
    枚举括号填空题：( ) op b = c / a op ( ) = c。
    已知项按 MIN_NUM 过滤，挖空处允许 0。
    """
    lo = MIN_NUM
    items = []
    seen = set()

    def add(op, a, b, c, pos):
        key = (op, a, b, c, pos)
        if key in seen:
            return
        seen.add(key)
        items.append((key, (op, a, b, c, pos)))

    for a in range(0, max_num + 1):
        for b in range(0, max_num - a + 1):
            c = a + b
            if c > max_num:
                continue
            if b >= lo and c >= lo:
                add('+', a, b, c, 'left')
            if a >= lo and c >= lo:
                add('+', a, b, c, 'right')

    for a in range(0, max_num + 1):
        for b in range(0, a + 1):
            c = a - b
            if b >= lo and c >= lo:
                add('-', a, b, c, 'left')
            if a >= lo and c >= lo:
                add('-', a, b, c, 'right')

    return items


def fill_op_items(max_num):
    """
    填符号题库：a ○ b = c，学生填 + 或 −。
      - a, b, c ∈ [0, max_num]
      - 排除 b == 0（+0 和 −0 都成立，无唯一解）
    返回 [(key, (a, op, b, c)), ...]，key 保留原始顺序以允许 2+3 与 3+2 同时出现。
    """
    items = []
    seen = set()
    for a in range(0, max_num + 1):
        for b in range(1, max_num + 1):
            s = a + b
            if s <= max_num:
                key = ('+', a, b, s)
                if key not in seen:
                    seen.add(key)
                    items.append((key, (a, '+', b, s)))
            d = a - b
            if d >= 0:
                key = ('-', a, b, d)
                if key not in seen:
                    seen.add(key)
                    items.append((key, (a, '-', b, d)))
    return items


def chain_sub_items(max_num):
    """
    枚举连减题 a - b - c，约束结果 >= 0。
    返回 [(key, (a, b, c)), ...]。
    """
    items = []
    seen = set()
    for a in range(0, max_num + 1):
        for b in range(0, a + 1):
            for c in range(0, a - b + 1):
                key = (a, b, c)
                if key in seen:
                    continue
                seen.add(key)
                items.append((key, (a, b, c)))
    return items


def chain_add_items(max_num):
    """
    枚举连加题 a + b + c，约束：
      - 所有数字 ∈ [1, max_num]（避免 0 作加数）
      - 结果 a + b + c ∈ [1, max_num]
    返回 [(key, (a, b, c)), ...]。
    """
    items = []
    seen = set()
    for a in range(1, max_num + 1):
        for b in range(1, max_num + 1 - a):
            for c in range(1, max_num + 1 - a - b):
                key = (a, b, c)
                if key in seen:
                    continue
                seen.add(key)
                items.append((key, (a, b, c)))
    return items


def chain_mix_items(max_num, mixed_only=True):
    """
    枚举连加连减混合题 a op1 b op2 c，约束：
      - 所有数字 ∈ [0, max_num]
      - 中间结果 a op1 b ∈ [0, max_num]
      - 最终结果 (a op1 b) op2 c ∈ [0, max_num]
      - 排除任意操作数为 0 的平凡题（0 不参与变化，等于只有一次运算）
      - mixed_only=True 时只保留「一加一减」的混合题（照片中的题型）
    返回 [(key, (a, op1, b, op2, c)), ...]。
    """
    items = []
    seen = set()
    ops = ('+', '-')
    for a in range(1, max_num + 1):
        for op1 in ops:
            for b in range(1, max_num + 1):
                mid = a + b if op1 == '+' else a - b
                if mid < 0 or mid > max_num:
                    continue
                for op2 in ops:
                    if mixed_only and op1 == op2:
                        continue
                    for c in range(1, max_num + 1):
                        result = mid + c if op2 == '+' else mid - c
                        if result < 0 or result > max_num:
                            continue
                        key = (a, op1, b, op2, c)
                        if key in seen:
                            continue
                        seen.add(key)
                        items.append((key, (a, op1, b, op2, c)))
    return items


def decompose_tree_items(max_num):
    """分解树题库：total -> part1 + ?"""
    items = []
    for total in range(3, max_num + 1):
        for part1 in range(1, total):
            items.append((('dec', total, part1), ('dec', total, part1)))
    return items


def compose_tree_items(max_num):
    """组成树题库：p1 + p2 -> ?"""
    items = []
    seen = set()
    for a in range(1, max_num):
        for b in range(1, max_num - a + 1):
            key = ('com', min(a, b), max(a, b))
            if key not in seen:
                seen.add(key)
                items.append((key, ('com', a, b)))
    return items
