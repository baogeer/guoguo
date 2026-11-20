"""填符号专项练习（PDF）。

题目形如：
    5 ◯ 2 = 7     8 ◯ 7 = 1
学生在 ◯ 里填 + 或 −。
"""

from ..core import (setup_document, save_as_pdf, grid_layout,
                    add_standalone_header, add_question_table)
from .generators import fill_op_items
from .renderers import add_fill_op_question


IDEAL_COLS = 5
ROW_HEIGHT_CM = 1.5


def _render(para, data):
    a, _op, b, c = data
    add_fill_op_question(para, a, b, c)


def add_section(doc, count, max_num, title=None, rows=None):
    if rows is None:
        rows, _ = grid_layout(count, IDEAL_COLS)
    return add_question_table(doc, rows, IDEAL_COLS, ROW_HEIGHT_CM,
                              fill_op_items(max_num), 'fop',
                              _render, count=count)


def save(count=40, pages=1, max_num=10, filename=None, keep_docx=False):
    """
    生成填符号专项练习 PDF。
      count    — 每页题目数量
      pages    — 页数
      max_num  — 数字范围上限
    """
    if filename is None:
        filename = f"填符号_{max_num}以内_{count}题x{pages}页.pdf"

    rows, cols = grid_layout(count, IDEAL_COLS)
    doc = setup_document()
    for page in range(pages):
        add_standalone_header(
            doc, f"{max_num}以内加减法填符号专项练习",
            tip_text='在 ◯ 里填上 + 或 −。',
            page_break_before=(page > 0))
        add_question_table(doc, rows, cols, ROW_HEIGHT_CM,
                           fill_op_items(max_num), 'fop', _render)

    save_as_pdf(doc, filename, keep_docx=keep_docx)
    print(f"已生成 {pages} 页，每页 {rows}×{cols}={rows * cols} 题 "
          f"（{max_num} 以内填符号）→ {filename}")
