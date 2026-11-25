"""应用题练习（PDF）。

题目形如：
    小明有 2 个苹果，又买了 3 个，一共有多少个苹果？
    ▢ ○ ▢ ＝ ▢

图片来源：5以内的应用题(1)(2) + 一年级应用题口诀
"""

import random

from docx.shared import Cm, Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import (WD_TABLE_ALIGNMENT, WD_ROW_HEIGHT_RULE,
                             WD_CELL_VERTICAL_ALIGNMENT)

from ..core import (setup_document, save_as_pdf, grid_layout,
                    add_standalone_header, fill_cells,
                    set_table_cell_margins_zero, hide_table_borders)
from .generators import word_problem_items
from .renderers import add_word_problem_question


IDEAL_COLS = 2
ROW_HEIGHT_CM = 3.2


def add_section(doc, count, max_num, title=None, rows=None):
    pool = word_problem_items(max_num)
    if not pool:
        return 0
    if rows is None:
        rows, _ = grid_layout(count, IDEAL_COLS)

    actual = min(count, rows * IDEAL_COLS)
    cells_data = fill_cells(rows, IDEAL_COLS,
                            lambda r, c: ('wp', pool), count=actual)

    table = doc.add_table(rows=rows, cols=IDEAL_COLS)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_cell_margins_zero(table)

    for r in range(rows):
        row = table.rows[r]
        row.height = Cm(ROW_HEIGHT_CM)
        row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
        for c in range(IDEAL_COLS):
            idx = r * IDEAL_COLS + c
            cell = table.cell(r, c)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            # 加一个左边框让两列之间有分隔
            if c > 0:
                tcPr = cell._tc.get_or_add_tcPr()
                tcBorders = OxmlElement('w:tcBorders')
                left = OxmlElement('w:left')
                left.set(qn('w:val'), 'single')
                left.set(qn('w:sz'), '4')
                left.set(qn('w:color'), 'C0C0C0')
                tcBorders.append(left)
                tcPr.append(tcBorders)
            if idx < actual:
                _key, (text, op, a, b) = cells_data[idx]
                add_word_problem_question(cell, text, op, a, b)
    return actual


def save(count=8, pages=1, max_num=5, filename=None, keep_docx=False):
    if filename is None:
        filename = f"应用题_{max_num}以内_{count}题x{pages}页.pdf"

    rows, cols = grid_layout(count, IDEAL_COLS)
    doc = setup_document(left_margin=1.0, right_margin=1.0)
    for page in range(pages):
        add_standalone_header(
            doc, f"{max_num}以内应用题练习",
            color=(0x00, 0x70, 0xC0), title_size=22,
            page_break_before=(page > 0))
        add_section(doc, count, max_num, rows=rows)

    save_as_pdf(doc, filename, keep_docx=keep_docx)
    print(f"已生成 {pages} 页，每页 {rows}×{cols}={rows * cols} 题 "
          f"（{max_num} 以内应用题）→ {filename}")
