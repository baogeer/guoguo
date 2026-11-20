"""括号填空专项练习（PDF）。

题目形如：
    ( ) + 3 = 7     9 − ( ) = 3
"""

from ..core import (setup_document, save_as_pdf, grid_layout,
                    add_standalone_header, add_question_table)
from .generators import blank_fill_items
from .renderers import add_blank_fill_question


IDEAL_COLS = 5
ROW_HEIGHT_CM = 1.5


def _render(para, data):
    op, a, b, c, pos = data
    add_blank_fill_question(para, op, a, b, c, pos, blank='(　　)')


def add_section(doc, count, max_num, title=None, rows=None):
    if rows is None:
        rows, _ = grid_layout(count, IDEAL_COLS)
    return add_question_table(doc, rows, IDEAL_COLS, ROW_HEIGHT_CM,
                              blank_fill_items(max_num), 'bf',
                              _render, count=count)


def save(count=60, pages=1, max_num=10, filename=None, keep_docx=False):
    """生成括号填空专项练习 PDF。"""
    if filename is None:
        filename = f"括号填空_{max_num}以内_{count}题x{pages}页.pdf"

    rows, cols = grid_layout(count, IDEAL_COLS)
    doc = setup_document()
    for page in range(pages):
        add_standalone_header(
            doc, f"{max_num}以内加减法括号填空练习",
            tip_text='在括号里填上合适的数。',
            page_break_before=(page > 0))
        add_question_table(doc, rows, cols, ROW_HEIGHT_CM,
                           blank_fill_items(max_num), 'bf', _render)

    save_as_pdf(doc, filename, keep_docx=keep_docx)
    print(f"已生成 {pages} 页，每页 {rows}×{cols}={rows * cols} 题 "
          f"（{max_num} 以内括号填空）→ {filename}")
