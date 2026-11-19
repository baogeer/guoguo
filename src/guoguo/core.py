"""共享工具：文档设置、表格辅助、去重填充、PDF 转换。"""

import os
import random
import tempfile

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import (WD_TABLE_ALIGNMENT, WD_ROW_HEIGHT_RULE,
                             WD_CELL_VERTICAL_ALIGNMENT)

MIN_NUM = 3


# ── 去重填充 ─────────────────────────────────────────────

def fill_cells(rows, cols, items_for, count=None):
    """
    通用填充器：items_for(r, c) -> (pool_key, items_list)。
    保证相邻单元格（左右、上下）不会出现相同题目。
    只填前 count 个单元格（默认填满 rows*cols），其余留空。
    题库用完时重新洗牌补充（小 max_num 时题目会重复）。
    """
    total = rows * cols
    n = total if count is None else max(0, min(count, total))
    queues = {}
    order = []
    for i in range(n):
        r, c = divmod(i, cols)
        pool_key, items = items_for(r, c)
        if not items:
            raise ValueError(f'题库为空：{pool_key}')
        queue = queues.get(pool_key)
        if not queue:
            queue = list(items)
            random.shuffle(queue)
            queues[pool_key] = queue
        order.append(queue.pop())

    keys = [None] * n
    for i in range(n):
        r, c = divmod(i, cols)
        left_key = keys[i - 1] if c > 0 else None
        up_key = keys[i - cols] if r > 0 else None
        if order[i][0] in (left_key, up_key):
            for j in range(i + 1, n):
                if order[j][0] not in (left_key, up_key):
                    order[i], order[j] = order[j], order[i]
                    break
        keys[i] = order[i][0]
    return order


# ── 表格辅助 ─────────────────────────────────────────────

def set_table_cell_margins_zero(table):
    tblPr = table._tbl.tblPr
    for old in tblPr.findall(qn('w:tblCellMar')):
        tblPr.remove(old)
    tblCellMar = OxmlElement('w:tblCellMar')
    for tag in ('top', 'left', 'bottom', 'right'):
        node = OxmlElement(f'w:{tag}')
        node.set(qn('w:w'), '0')
        node.set(qn('w:type'), 'dxa')
        tblCellMar.append(node)
    tblPr.append(tblCellMar)


def hide_table_borders(table):
    tblPr = table._tbl.tblPr
    tblBorders = OxmlElement('w:tblBorders')
    for border_name in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), 'none')
        tblBorders.append(border)
    tblPr.append(tblBorders)


def lock_table_layout(table):
    tblPr = table._tbl.tblPr
    tblLayout = OxmlElement('w:tblLayout')
    tblLayout.set(qn('w:type'), 'fixed')
    tblPr.append(tblLayout)


# ── 文档设置 ─────────────────────────────────────────────

def setup_document(top_margin=0.9, bottom_margin=0.9,
                   left_margin=1.0, right_margin=1.0):
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(top_margin)
    section.bottom_margin = Cm(bottom_margin)
    section.left_margin = Cm(left_margin)
    section.right_margin = Cm(right_margin)

    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.space_after = Pt(0)
    return doc


def add_page_header(doc, title_text=None, page_break_before=False,
                    style='simple'):
    """
    添加页面标题和信息行。

    style='simple'   — 普通标题（14pt），用于综合/基础练习
    style='adjacent' — 彩色大标题（20pt），用于相邻数专项
    """
    if style == 'adjacent':
        title = doc.add_paragraph()
        if page_break_before:
            title.paragraph_format.page_break_before = True
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = title.add_run("新一年级上册数学")
        r1.font.size = Pt(20)
        r1.font.bold = True
        r2 = title.add_run("相邻数")
        r2.font.size = Pt(20)
        r2.font.bold = True
        r2.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
        r3 = title.add_run("专项练习")
        r3.font.size = Pt(20)
        r3.font.bold = True
        r3.font.color.rgb = RGBColor(0x00, 0x70, 0xC0)
        title.paragraph_format.space_after = Pt(6)

        info = doc.add_paragraph()
        info.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = info.add_run(
            '姓名：__________    班级：__________    日期：__________')
        r.font.size = Pt(12)
        info.paragraph_format.space_after = Pt(6)
    else:
        title = doc.add_paragraph()
        if page_break_before:
            title.paragraph_format.page_break_before = True
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title.add_run(title_text or '')
        run.font.size = Pt(14)
        run.font.bold = True
        title.paragraph_format.space_after = Pt(1)

        info = doc.add_paragraph()
        info.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = info.add_run('姓名：__________    日期：__________')
        r.font.size = Pt(10)
        info.paragraph_format.space_after = Pt(3)


def add_section_title(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(11)
    run.font.bold = True
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)


# ── 独立练习页头（各题型 save() 用） ─────────────────────

def add_standalone_header(doc, title_text, color=(0xC0, 0x00, 0x00),
                          title_size=20, tip_text=None,
                          page_break_before=False):
    """用于单题型 PDF（xxx.save()）的页头：大标题 + 姓名行 + 可选提示。"""
    title = doc.add_paragraph()
    if page_break_before:
        title.paragraph_format.page_break_before = True
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(title_text)
    run.font.size = Pt(title_size)
    run.font.bold = True
    run.font.color.rgb = RGBColor(*color)
    title.paragraph_format.space_after = Pt(6)

    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = info.add_run(
        '姓名：__________    日期：__________    用时：__________')
    r.font.size = Pt(11)
    info.paragraph_format.space_after = Pt(4)

    if tip_text:
        tip = doc.add_paragraph()
        r = tip.add_run(tip_text)
        r.font.size = Pt(12)
        r.font.bold = True
        tip.paragraph_format.space_after = Pt(4)


# ── 通用题目表格 ─────────────────────────────────────────

def add_question_table(doc, rows, cols, row_height_cm, items, pool_key,
                       render, count=None):
    """
    统一的题目表格渲染：rows×cols 单元格，用 render(para, data) 写题。

    items     — [(key, data), ...] 题库
    pool_key  — 相邻去重用的池标识
    render    — 回调，签名 render(paragraph, data)；data 为 items 第二项
    count     — 实际要填的题数（默认填满整表）；超出部分留空
    返回实际写入的题数。
    """
    if rows <= 0 or not items:
        return 0
    table = doc.add_table(rows=rows, cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_cell_margins_zero(table)

    n = rows * cols if count is None else max(0, min(count, rows * cols))
    cells = fill_cells(rows, cols, lambda r, c: (pool_key, items), count=n)

    i = 0
    for r in range(rows):
        row = table.rows[r]
        row.height = Cm(row_height_cm)
        row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
        for c in range(cols):
            cell = table.cell(r, c)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            para = cell.paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.space_before = Pt(0)
            para.paragraph_format.space_after = Pt(0)
            if i >= n:
                continue
            render(para, cells[i][1])
            i += 1
    return n


# ── PDF 转换 ─────────────────────────────────────────────

def docx_to_pdf(docx_path, pdf_path, tries=3):
    import time
    import win32com.client
    import pythoncom
    last = None
    for attempt in range(tries):
        pythoncom.CoInitialize()
        word = None
        try:
            word = win32com.client.DispatchEx('Word.Application')
            word.Visible = False
            word.DisplayAlerts = 0
            doc = word.Documents.Open(os.path.abspath(docx_path),
                                      ReadOnly=True)
            try:
                pages = int(doc.ComputeStatistics(2))
                doc.SaveAs(os.path.abspath(pdf_path), FileFormat=17)
                return pages
            finally:
                doc.Close(False)
        except Exception as exc:
            last = exc
            time.sleep(1.0 + attempt)
        finally:
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
    raise RuntimeError(f'Word 转 PDF 失败：{last}')


def save_as_pdf(doc, filename, keep_docx=False):
    """将 python-docx Document 保存为 PDF，可选保留中间 docx。返回页数。"""
    if keep_docx:
        tmp_docx = os.path.splitext(filename)[0] + '.docx'
        doc.save(tmp_docx)
        return docx_to_pdf(tmp_docx, filename)
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
        tmp_docx = tmp.name
    try:
        doc.save(tmp_docx)
        return docx_to_pdf(tmp_docx, filename)
    finally:
        try:
            os.remove(tmp_docx)
        except OSError:
            pass


# ── 自动布局 ─────────────────────────────────────────────

SECTION_TITLE_CM = 0.65   # 每个板块小标题占的高度
HEADER_CM = 1.45          # 页头（标题 + 姓名行）占的高度
SPACER_CM = 0.25          # 板块之间的空行，同时防止 Word 把相邻表格合并
PAGE_SAFETY_CM = 0.15     # 页面底部余量（真实页数还会由 Word 实测兜底）


def grid_layout(count, cols):
    """固定列数布局：列数不变，末行可以不满。返回 (rows, cols)。"""
    if count <= 0:
        return 0, cols
    return (count + cols - 1) // cols, cols


def page_budget_cm(doc):
    """一页可用来放题目的总高度（cm），已扣掉页头和底部余量。"""
    section = doc.sections[0]
    usable = (section.page_height.cm - section.top_margin.cm
              - section.bottom_margin.cm)
    return usable - HEADER_CM - PAGE_SAFETY_CM


def allocate_rows(desired_rows, row_heights, fixed_costs, budget_cm,
                  max_rows=None):
    """
    在总高度 budget_cm 内分配每个板块的行数。

    fixed_costs[i] 是第 i 块除行之外的固定开销（小标题、空行）。
    每块的行数不超过 max_rows[i]（默认用 desired_rows 自身当上限）。

    预算还有余时，用 round-robin 把多余行均匀发给还没到上限的块；
    超预算时从行数最多的一块削减（大板块吸收裁剪）。
    每块至少保留 1 行，保证每个题型都出现。
    """
    rows = [max(1, r) for r in desired_rows]
    if not rows:
        return rows
    if max_rows is None:
        max_rows = list(rows)
    else:
        max_rows = [max(1, m) for m in max_rows]

    def total():
        return sum(f + r * h
                   for f, r, h in zip(fixed_costs, rows, row_heights))

    while total() > budget_cm:
        best_i, best_rows = None, 0
        for i, r in enumerate(rows):
            if r > 1 and r > best_rows:
                best_i, best_rows = i, r
        if best_i is None:
            break
        rows[best_i] -= 1

    # 预算还有余 → 均匀加行，但不超过各自上限
    cursor = 0
    guard = 0
    while guard < 10_000:
        guard += 1
        progressed = False
        for _ in range(len(rows)):
            i = cursor % len(rows)
            cursor += 1
            if rows[i] >= max_rows[i]:
                continue
            if total() + row_heights[i] > budget_cm:
                continue
            rows[i] += 1
            progressed = True
            break
        if not progressed:
            break
    return rows


def add_spacer(doc):
    """板块之间的小空行。必须存在，否则 Word 会把相邻两张表合并成一张。"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = Pt(4)
    p.add_run('').font.size = Pt(4)
    return p


# ── 页数检测 ─────────────────────────────────────────────

def count_pages(doc):
    """用 Word 统计 doc 的真实页数（保存临时 docx 后打开统计）。"""
    import win32com.client
    import pythoncom
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
        tmp_docx = tmp.name
    pythoncom.CoInitialize()
    word = None
    try:
        doc.save(tmp_docx)
        word = win32com.client.DispatchEx('Word.Application')
        word.Visible = False
        word.DisplayAlerts = 0
        opened = word.Documents.Open(os.path.abspath(tmp_docx), ReadOnly=True)
        try:
            return int(opened.ComputeStatistics(2))
        finally:
            opened.Close(False)
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()
        try:
            os.remove(tmp_docx)
        except OSError:
            pass
