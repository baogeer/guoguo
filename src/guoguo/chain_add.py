"""连加填空练习（PDF）。

题目形如：
    2 + 3 + 4 = ▢
    1 + 2 + 5 = ▢
"""

from .core import (setup_document, save_as_pdf, grid_layout,
                   add_standalone_header, add_question_table)
from .generators import chain_add_items
from .renderers import add_chain_add_question


IDEAL_COLS = 4
ROW_HEIGHT_CM = 1.5


def _render(para, data):
    add_chain_add_question(para, *data)


def add_section(doc, count, max_num, title=None, rows=None):
    if rows is None:
        rows, _ = grid_layout(count, IDEAL_COLS)
    return add_question_table(doc, rows, IDEAL_COLS, ROW_HEIGHT_CM,
                              chain_add_items(max_num), 'ca',
                              _render, count=count)


def save(count=30, pages=1, max_num=10, filename=None, keep_docx=False):
    """生成连加填空练习 PDF。"""
    if filename is None:
        filename = f"连加填空_{max_num}以内_{count}题x{pages}页.pdf"

    rows, cols = grid_layout(count, IDEAL_COLS)
    doc = setup_document(left_margin=1.2, right_margin=1.2)
    for page in range(pages):
        add_standalone_header(
            doc, f"{max_num}以内连加填空练习题",
            color=(0xC0, 0x50, 0x4D), title_size=22,
            page_break_before=(page > 0))
        add_question_table(doc, rows, cols, ROW_HEIGHT_CM,
                           chain_add_items(max_num), 'ca', _render)

    save_as_pdf(doc, filename, keep_docx=keep_docx)
    print(f"已生成 {pages} 页，每页 {rows}×{cols}={rows * cols} 题 "
          f"（{max_num} 以内连加填空）→ {filename}")
