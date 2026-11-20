"""相邻数专项练习（PDF）。"""

from docx.shared import Cm
from docx.enum.table import (WD_TABLE_ALIGNMENT, WD_ROW_HEIGHT_RULE,
                             WD_CELL_VERTICAL_ALIGNMENT)

from ..core import (setup_document, fill_cells, set_table_cell_margins_zero,
                    hide_table_borders, lock_table_layout,
                    add_page_header, save_as_pdf, grid_layout)
from .generators import adjacent_items
from .renderers import write_adjacent_to_cell


IDEAL_COLS = 4
ROW_HEIGHT_CM = 1.6


def _add_table(doc, rows, cols, max_num, count=None):
    if rows <= 0:
        return 0
    table = doc.add_table(rows=rows, cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hide_table_borders(table)
    set_table_cell_margins_zero(table)
    lock_table_layout(table)

    items = adjacent_items(max_num)
    n = rows * cols if count is None else max(0, min(count, rows * cols))
    cells = fill_cells(rows, cols, lambda r, c: ('adj', items), count=n)

    i = 0
    cell_width = Cm(18.8 / cols)
    for r in range(rows):
        row = table.rows[r]
        row.height = Cm(ROW_HEIGHT_CM)
        row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
        for c in range(cols):
            cell = table.cell(r, c)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.width = cell_width
            if i >= n:
                continue
            _, q_type, a, b = cells[i]
            i += 1
            write_adjacent_to_cell(cell, q_type, a, b)
    return n


def add_section(doc, count, max_num, title=None, rows=None):
    if rows is None:
        rows, cols = grid_layout(count, IDEAL_COLS)
    else:
        cols = IDEAL_COLS
    return _add_table(doc, rows, cols, max_num, count=count)


def save(count=12, pages=1, max_num=12, filename=None, keep_docx=False):
    """
    生成相邻数专项练习 PDF。
      count    — 每页题目数量
      pages    — 页数
      max_num  — 数字范围上限
    """
    if filename is None:
        filename = f"相邻数专项练习_{max_num}以内_{count}题x{pages}页.pdf"

    rows, cols = grid_layout(count, IDEAL_COLS)

    doc = setup_document(top_margin=1.0, bottom_margin=1.0)
    for page in range(pages):
        add_page_header(doc, page_break_before=(page > 0), style='adjacent')
        _add_table(doc, rows, cols, max_num)

    save_as_pdf(doc, filename, keep_docx=keep_docx)
    print(f"已生成 {pages} 页，每页 {rows}×{cols}={rows * cols} 题 "
          f"（{max_num} 以内相邻数）→ {filename}")
