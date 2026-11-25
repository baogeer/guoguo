"""幼儿园大班短文生成入口（规整版，无田字格/四线三格）。

运行：python main_chinese.py

- 从 src/chinese/article.py 的故事模板里随机抽一篇
- 拼音在上、汉字在下，每格等宽，整篇间距一致
- A4 一页之内；长句按标点自动折行
- 输出到 大班文章/
"""

import os
import time

from docx.shared import Pt, Cm, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import (WD_TABLE_ALIGNMENT, WD_ROW_HEIGHT_RULE,
                             WD_CELL_VERTICAL_ALIGNMENT)

from src.core import setup_document, save_as_pdf
from src.chinese.ai_article import generate_article_ai
from src.chinese.article import generate_article as generate_article_local


OUT_DIR = '大班文章'

CELL_W_CM = 1.20
HANZI_H_CM = 1.30
PINYIN_H_CM = 0.80
HANZI_PT = 30
PINYIN_PT = 14
INTRA_GAP_PT = 1    # 同一句被折行时，子行之间的小空
INTER_GAP_PT = 5    # 句与句之间的空
MAX_UNITS_PER_ROW = 15


# ── XML 工具 ─────────────────────────────────────────────

def _set_tcMar_zero(cell):
    tcPr = cell._tc.get_or_add_tcPr()
    for old in tcPr.findall(qn('w:tcMar')):
        tcPr.remove(old)
    tcMar = OxmlElement('w:tcMar')
    for side in ('top', 'left', 'bottom', 'right'):
        m = OxmlElement(f'w:{side}')
        m.set(qn('w:w'), '0')
        m.set(qn('w:type'), 'dxa')
        tcMar.append(m)
    tcPr.append(tcMar)


def _hide_table_borders(table):
    tblPr = table._tbl.tblPr
    for old in tblPr.findall(qn('w:tblBorders')):
        tblPr.remove(old)
    tblBorders = OxmlElement('w:tblBorders')
    for name in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        b = OxmlElement(f'w:{name}')
        b.set(qn('w:val'), 'nil')
        tblBorders.append(b)
    tblPr.append(tblBorders)


def _lock_table_layout(table, cols, col_w_cm):
    """锁定表格列宽（没有这几项的话 Word 会把表格拉成页宽）。"""
    tbl = table._tbl
    tblPr = tbl.tblPr
    col_w_twips = int(col_w_cm * 567)
    total_w_twips = col_w_twips * cols

    for old in tblPr.findall(qn('w:tblLayout')):
        tblPr.remove(old)
    el = OxmlElement('w:tblLayout')
    el.set(qn('w:type'), 'fixed')
    tblPr.append(el)

    for old in tblPr.findall(qn('w:tblW')):
        tblPr.remove(old)
    tblW = OxmlElement('w:tblW')
    tblW.set(qn('w:type'), 'dxa')
    tblW.set(qn('w:w'), str(total_w_twips))
    tblPr.append(tblW)

    old_grid = tbl.find(qn('w:tblGrid'))
    if old_grid is not None:
        tbl.remove(old_grid)
    grid = OxmlElement('w:tblGrid')
    for _ in range(cols):
        gc = OxmlElement('w:gridCol')
        gc.set(qn('w:w'), str(col_w_twips))
        grid.append(gc)
    tblPr.addnext(grid)

    for row in table.rows:
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            for old in tcPr.findall(qn('w:tcW')):
                tcPr.remove(old)
            tcW = OxmlElement('w:tcW')
            tcW.set(qn('w:type'), 'dxa')
            tcW.set(qn('w:w'), str(col_w_twips))
            tcPr.insert(0, tcW)
    table.autofit = False


# ── 单元格填充 ───────────────────────────────────────────

def _fill_cell(cell, text, is_pinyin):
    _set_tcMar_zero(cell)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    para = cell.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = para.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    run = para.add_run(text or '')
    run.font.size = Pt(PINYIN_PT if is_pinyin else HANZI_PT)
    if is_pinyin:
        run.font.name = 'Arial'
    else:
        run.font.name = '楷体'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')


# ── 行渲染 ───────────────────────────────────────────────

def _add_grid_row(doc, units):
    n = len(units)
    if n == 0:
        return
    tbl = doc.add_table(rows=2, cols=n)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    _lock_table_layout(tbl, cols=n, col_w_cm=CELL_W_CM)
    _hide_table_borders(tbl)

    tbl.rows[0].height = Cm(PINYIN_H_CM)
    tbl.rows[0].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    tbl.rows[1].height = Cm(HANZI_H_CM)
    tbl.rows[1].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY

    for c, (ch, py) in enumerate(units):
        _fill_cell(tbl.cell(0, c), py, is_pinyin=True)
        _fill_cell(tbl.cell(1, c), ch, is_pinyin=False)


def _wrap(units, max_per_row):
    """按标点折行。允许每行向后吃 1~2 个结尾标点，避免「。」单独一行。"""
    rows = []
    i, n = 0, len(units)
    while i < n:
        remaining = n - i
        if remaining <= max_per_row:
            rows.append(units[i:])
            break
        # 第 max 位往后紧跟的是标点 → 让它和前面的字一起放进这行
        tail = i + max_per_row
        extend = 0
        while tail + extend < n and units[tail + extend][1] == '' and extend < 2:
            extend += 1
        if extend > 0:
            rows.append(units[i:tail + extend])
            i = tail + extend
            continue
        # 正常找标点切
        cut = -1
        for j in range(min(i + max_per_row, n) - 1, i, -1):
            if units[j][1] == '':
                cut = j + 1
                break
        if cut <= i:
            cut = i + max_per_row
        rows.append(units[i:cut])
        i = cut
    return rows


def _add_spacer(doc, pt):
    sp = doc.add_paragraph()
    pf = sp.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(pt)
    sp.add_run('').font.size = Pt(max(1, pt - 1))


def _add_line(doc, units):
    if not units:
        _add_spacer(doc, INTER_GAP_PT)
        return
    rows = _wrap(units, MAX_UNITS_PER_ROW)
    for i, row in enumerate(rows):
        _add_grid_row(doc, row)
        # 句内折行用小空；一句画完给一个大空，视觉上把句子分开
        gap = INTER_GAP_PT if i == len(rows) - 1 else INTRA_GAP_PT
        _add_spacer(doc, gap)


def _add_title(doc, title, page_break_before=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if page_break_before:
        p.paragraph_format.page_break_before = True
    run = p.add_run(title)
    run.font.size = Pt(22)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    run.font.name = '楷体'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')
    p.paragraph_format.space_after = Pt(3)


def _render(articles):
    """articles: list of (title, lines)。每篇一页。"""
    doc = setup_document(top_margin=0.8, bottom_margin=0.6,
                         left_margin=1.0, right_margin=1.0)
    for i, (title, lines) in enumerate(articles):
        _add_title(doc, title, page_break_before=(i > 0))
        for units in lines:
            _add_line(doc, units)
    return doc


def _generate_one():
    """生成单篇 (标题, lines)。AI 失败回退到本地模板。"""
    try:
        title, lines = generate_article_ai()
        return title, lines, 'AI (DeepSeek)'
    except Exception as exc:
        print(f'[降级] AI 生成失败：{exc}')
        print('[降级] 改用本地模板生成')
        title, lines = generate_article_local()
        return title, lines, '本地模板'


def main(sets=1):
    """
    sets：生成几篇文章（也就是 PDF 的页数）。每页一篇，独立随机。
    sets=1 时文件名用篇名；sets>1 时打包成一个合集 PDF。
    """
    sets = max(1, int(sets))

    articles = []
    sources = []
    for i in range(sets):
        print(f'[{i + 1}/{sets}] 生成中…')
        title, lines, source = _generate_one()
        articles.append((title, lines))
        sources.append(source)
        preview = ''.join(''.join(ch for ch, _ in line) for line in lines)
        print(f'  ✓ {title}：{preview[:30]}…')

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = time.strftime('%Y%m%d_%H%M%S')
    if sets == 1:
        fname = f'{articles[0][0]}_{stamp}.pdf'
    else:
        fname = f'大班短文合集_{sets}篇_{stamp}.pdf'
    pdf_path = os.path.join(OUT_DIR, fname)

    doc = _render(articles)
    pages = save_as_pdf(doc, pdf_path)

    print()
    print(f'已生成：{pdf_path}（{pages} 页）')
    print(f'来源：{", ".join(sorted(set(sources)))}')
    for i, ((title, _), src) in enumerate(zip(articles, sources)):
        print(f'  第 {i + 1} 页：{title}（{src}）')
    if pages != sets:
        print(f'⚠ 实际 {pages} 页 ≠ 预期 {sets} 页：某篇超出了单页上限')


if __name__ == '__main__':
    sets = 100
    main(sets)
