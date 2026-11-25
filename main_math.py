"""小学数学练习题生成器。

修改下方 TASKS 和 __main__ 里的 sets，运行 python main_math.py，
生成一份 PDF，里面包含 sets 套完全独立的数学练习（每套一页，题目各自随机）。

TASKS 里的 `题数` 是「推荐值」：
  - 题型多时，程序会自动减少每块题数以保证单套一页装得下；
  - 题型少、页面有空余时，程序会自动增加题数填满页面；
  - 每块至少保留 1 行，不会超过题库容量或页面上限。

语文题的入口请看 main_chinese.py（规划中）。生成逻辑分别放在
src/math/ 和 src/chinese/，共享 src/core.py 的排版工具。
"""

import os
import shutil
import tempfile

from src.math import (adjacent, blank_fill, chain_add, chain_sub, chain_mix,
                      compare, fill_op, word_problem)
from src.core import (setup_document, save_as_pdf, add_page_header,
                      add_section_title, add_spacer, grid_layout,
                      page_budget_cm, allocate_rows,
                      SECTION_TITLE_CM, SPACER_CM)
from src.math.generators import (adjacent_items, blank_fill_items,
                                 chain_add_items, chain_sub_items,
                                 chain_mix_items, compare_expr_items,
                                 fill_op_items, word_problem_items)


# ============================================================
# 要生成的任务列表（直接在这里改）
# ============================================================
#
# 格式：('题型', 推荐题数, max_num)
#   推荐题数：这一块想出的题数（程序会根据页面空间自动增减，
#            保证单套一页装得下）。
#   max_num ：数字范围上限，例如 max_num=10 表示所有数字和结果都在 [0, 10]。
# ============================================================

TASKS = [
    # 例：2 + 3 + 4 = ▢  ／  1 + 2 + 5 = ▢
    # ('chain-add',    20,   10),

    # 例：10 - 5 - 4 = ▢  ／  9 - 2 - 3 = ▢
    # ('chain-sub',    20,   10),

    # 例：2 + 5 - 4 = ▢  ／  7 - 2 + 2 = ▢
    ('chain-mix',    20,   10),

    # 例：（ ）4（ ） ／ 1（ ）3
    # ('adjacent',     8,    12),

    # 例：( ) + 3 = 7  ／  9 - ( ) = 3
    # ('blank-fill',   15,   10),

    # 例：5 ◯ 2 = 7  ／  8 ◯ 7 = 1（填 + 或 −）
    # ('fill-op',      20,   10),

    # 例：3 + 3 ◯ 3 + 2  ／  10 - 7 ◯ 1 + 2
    # 4 列布局，在◯里填 >、< 或 =
    ('compare',      16,   10),

    # 例：小明有 2 个苹果，又买了 3 个，一共有多少个苹果？
    # 2 列布局，max_num 建议 10
    ('word-problem', 6,    10),
]


# ============================================================
# 不要动下面
# ============================================================

SHEETS = {
    'adjacent':      (adjacent,      '相邻数',       adjacent_items),
    'blank-fill':    (blank_fill,    '括号填空',     blank_fill_items),
    'chain-add':     (chain_add,     '连加',         chain_add_items),
    'chain-sub':     (chain_sub,     '连减',         chain_sub_items),
    'chain-mix':     (chain_mix,     '连加连减混合', chain_mix_items),
    'compare':       (compare,       '比大小',       compare_expr_items),
    'fill-op':       (fill_op,       '填符号',       fill_op_items),
    'word-problem':  (word_problem,  '应用题',       word_problem_items),
}

SECTION_LABELS = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']


def _resolve(tasks):
    """过滤未知题型和空题库，返回可渲染的板块列表。"""
    resolved = []
    for name, count, max_num in tasks:
        if name not in SHEETS:
            print(f'跳过未知题型：{name}')
            continue
        module, zh_name, pool_fn = SHEETS[name]
        if count <= 0:
            print(f'跳过 {zh_name}：题数为 {count}')
            continue
        if not pool_fn(max_num):
            print(f'跳过 {zh_name}：max_num={max_num} 时题库为空，'
                  f'请把 max_num 调大')
            continue
        resolved.append({
            'name': name, 'module': module, 'zh': zh_name,
            'count': count, 'max_num': max_num,
            'cols': module.IDEAL_COLS, 'height': module.ROW_HEIGHT_CM,
        })
    return resolved


def _row_caps(sections, budget_cm, fixed_total_cm):
    """每块的行数上限：单块独占时，预算能装下的最大行数。

    allocate_rows 会按块数均分预算，上限只是防止无脑放大；
    实际上限由实测 _grow 中的 render_and_count 兜底。
    """
    caps = []
    for s in sections:
        avail = budget_cm - fixed_total_cm
        cap = max(1, int(avail / s['height']))
        caps.append(cap)
    return caps


def _render(sections, rows, sets=1):
    """渲染整篇文档：按 rows 把 TASKS 重复 sets 套，每套一页，题目各自随机。"""
    doc = setup_document()
    for s_idx in range(sets):
        add_page_header(doc, '一年级数学综合练习',
                        page_break_before=(s_idx > 0))
        for i, sec in enumerate(sections):
            n_rows = rows[i]
            count = n_rows * sec['cols']
            if i:
                add_spacer(doc)
            label = SECTION_LABELS[i] if i < len(SECTION_LABELS) else str(i + 1)
            add_section_title(doc, f'{label}、{sec["zh"]}')
            sec['module'].add_section(doc, count=count,
                                      max_num=sec['max_num'], rows=n_rows)

    # 回传第一套的实际题数，用于打印统计（每套结构相同）
    counts = [rows[i] * sec['cols'] for i, sec in enumerate(sections)]
    return doc, counts


def _shave(rows):
    """从行数最多的一块削掉一行，返回是否成功。"""
    best_i, best_rows = None, 0
    for i, r in enumerate(rows):
        if r > 1 and r > best_rows:
            best_i, best_rows = i, r
    if best_i is None:
        return False
    rows[best_i] -= 1
    return True


def _grow(rows, caps, render_and_count):
    """实测驱动均匀加行：round-robin 给未触顶的块 +1，翻页就撤回。

    allocate_rows 的估算偏乐观（Word 实际渲染略高于计算值），用真实页数兜底。
    """
    cursor = 0
    for _ in range(500):
        progressed = False
        for _ in range(len(rows)):
            i = cursor % len(rows)
            cursor += 1
            if rows[i] >= caps[i]:
                continue
            rows[i] += 1
            if render_and_count(rows) <= 1:
                progressed = True
                break
            rows[i] -= 1
            caps[i] = rows[i]  # 这块已到实际极限，别再试
        if not progressed:
            break


def main(sets=1):
    sets = max(1, int(sets))

    sections = _resolve(TASKS)
    if not sections:
        print('TASKS 里没有可生成的题目。')
        return

    heights = [s['height'] for s in sections]
    fixed = [SECTION_TITLE_CM + (SPACER_CM if i else 0.0)
             for i in range(len(sections))]

    probe_doc = setup_document()
    budget = page_budget_cm(probe_doc)
    caps = _row_caps(sections, budget, sum(fixed))

    # TASKS 里的推荐题数 → 每块初始行数。少题型时初始值偏小，_grow 会补足。
    desired = [max(1, grid_layout(s['count'], s['cols'])[0]) for s in sections]
    desired = [min(d, c) for d, c in zip(desired, caps)]
    rows = allocate_rows(desired, heights, fixed, budget, max_rows=caps)

    tmp_pdf = os.path.join(tempfile.gettempdir(), 'math_attempt.pdf')

    # 布局阶段只渲染一套测页数（整篇排版和单套一致），确定了行数再铺满 sets 套
    def render_and_count(rs):
        doc_try, _ = _render(sections, list(rs), sets=1)
        return save_as_pdf(doc_try, tmp_pdf)

    # 先按单套渲染一次；超页就从最大块削行到 ≤ 1 页。
    pages = None
    for _ in range(50):
        doc, _ = _render(sections, rows, sets=1)
        pages = save_as_pdf(doc, tmp_pdf)
        if pages <= 1:
            break
        if not _shave(rows):
            break
        print(f'[收紧] 实测 {pages} 页，继续减少行数 → {rows}')

    # 不超页：尝试均匀加行填满页面（遇翻页自动回退），用上限 caps 约束。
    if pages <= 1:
        _grow(rows, list(caps), render_and_count)

    # 用确定好的行数一次性渲染 sets 套
    doc, counts = _render(sections, rows, sets=sets)
    pages = save_as_pdf(doc, tmp_pdf)

    names = '+'.join(s['zh'] for s in sections)
    per_set = sum(counts)
    total = per_set * sets
    filename = f'综合练习_{names}_{sets}套共{total}题.pdf'
    shutil.move(tmp_pdf, filename)

    print(f'已生成 {pages} 页 PDF（{sets} 套 × 每套 {per_set} 题）：{filename}')
    if pages > sets:
        print(f'警告：实测 {pages} 页 > 预期 {sets} 页，单套可能装不下，'
              '请减少 TASKS 里的题型数量或调小 max_num。')
    print(f'每套 {per_set} 道题，分 {len(sections)} 块：')
    width = max(len(s['zh']) for s in sections)
    for i, (s, n, r) in enumerate(zip(sections, counts, rows)):
        label = SECTION_LABELS[i] if i < len(SECTION_LABELS) else str(i + 1)
        print(f'  {label}、{s["zh"]:<{width}} {n} 题'
              f'（{r} 行 × {s["cols"]} 列）')


if __name__ == '__main__':
    sets = 2
    main(sets)
