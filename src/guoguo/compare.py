"""比大小练习（PDF）。

题目形如：
    3 + 3 ◯ 3 + 2
    10 − 7 ◯ 1 + 2
"""

from .core import (setup_document, save_as_pdf, grid_layout,
                   add_standalone_header, add_question_table)
from .generators import compare_expr_items
from .renderers import add_compare_question


IDEAL_COLS = 4
ROW_HEIGHT_CM = 1.5


def _render(para, data):
    left, right = data
    add_compare_question(para, left, right)


def add_section(doc, count, max_num, title=None, rows=None):
    if rows is None:
        rows, _ = grid_layout(count, IDEAL_COLS)
    return add_question_table(doc, rows, IDEAL_COLS, ROW_HEIGHT_CM,
                              compare_expr_items(max_num), 'cmp',
                              _render, count=count)


def save(count=20, pages=1, max_num=10, filename=None, keep_docx=False):
    if filename is None:
        filename = f"比大小_{max_num}以内_{count}题x{pages}页.pdf"

    rows, cols = grid_layout(count, IDEAL_COLS)
    doc = setup_document()
    for page in range(pages):
        add_standalone_header(
            doc, f"{max_num}以内比大小练习",
            tip_text='在◯里填上 >、< 或 =。',
            page_break_before=(page > 0))
        add_question_table(doc, rows, cols, ROW_HEIGHT_CM,
                           compare_expr_items(max_num), 'cmp', _render)

    save_as_pdf(doc, filename, keep_docx=keep_docx)
    print(f"已生成 {pages} 页，每页 {rows}×{cols}={rows * cols} 题 "
          f"（{max_num} 以内比大小）→ {filename}")
