"""题目渲染：将题目数据写入 Word 单元格/段落。"""

from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH


# ── 字体工具 ─────────────────────────────────────────────

def _set_east_asia(run, font='宋体'):
    rpr = run._element.get_or_add_rPr()
    rpr.get_or_add_rFonts().set(qn('w:eastAsia'), font)


def _op_sym(op):
    """加减号统一：减号用全角「−」更醒目。"""
    return ' + ' if op == '+' else ' − '


# ── 加减法 ───────────────────────────────────────────────

def add_add_sub_question(para, text):
    run = para.add_run(text)
    run.font.size = Pt(11)


# ── 比大小 ───────────────────────────────────────────────

def _expr_text(expr):
    a, op, b, _ = expr
    return f"{a}{_op_sym(op)}{b}"


def add_compare_question(para, left, right):
    """left / right 形如 (a, op, b, value)。"""
    para.add_run(f"{_expr_text(left)} ").font.size = Pt(11)
    para.add_run("◯").font.size = Pt(14)
    para.add_run(f" {_expr_text(right)}").font.size = Pt(11)


# ── 括号填空 ─────────────────────────────────────────────

def add_blank_fill_question(para, op, a, b, c, blank_pos, blank='(　)'):
    if blank_pos == 'left':
        left, right = blank, str(b)
    else:
        left, right = str(a), blank
    run = para.add_run(f"{left}{_op_sym(op)}{right} = {c}")
    run.font.size = Pt(11)


# ── 填符号（照片中的题型）───────────────────────────────

def add_fill_op_question(para, a, b, c):
    """a ◯ b = c，学生在 ◯ 里填 + 或 −。"""
    run = para.add_run(f"{a} ")
    run.font.size = Pt(13)
    _set_east_asia(run)

    circle = para.add_run("◯")
    circle.font.size = Pt(14)
    _set_east_asia(circle)

    run = para.add_run(f" {b} = {c}")
    run.font.size = Pt(13)
    _set_east_asia(run)


# ── 连加 / 连减 / 混合 (统一) ───────────────────────────

def add_arithmetic_question(para, expr_text, answer='▢',
                            expr_size=14, answer_size=20):
    """
    统一的「算式 = 答案框」渲染：用于连加、连减、连加连减混合。
    expr_text 由各题型自己拼好（含空格和 − 号）。
    """
    run = para.add_run(f"{expr_text} = ")
    run.font.size = Pt(expr_size)
    run.font.name = 'Arial'
    _set_east_asia(run)

    box = para.add_run(answer)
    box.font.size = Pt(answer_size)
    box.font.name = 'SimSun'
    _set_east_asia(box)


def add_chain_sub_question(para, a, b, c):
    add_arithmetic_question(para, f"{a}{_op_sym('-')}{b}{_op_sym('-')}{c}")


def add_chain_add_question(para, a, b, c):
    add_arithmetic_question(para, f"{a}{_op_sym('+')}{b}{_op_sym('+')}{c}")


def add_chain_mix_question(para, a, op1, b, op2, c):
    add_arithmetic_question(
        para, f"{a}{_op_sym(op1)}{b}{_op_sym(op2)}{c}")


# ── 相邻数 ───────────────────────────────────────────────

def write_adjacent_to_cell(cell, q_type, a, b):
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(OxmlElement('w:noWrap'))

    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    for r in p.runs:
        r.text = ""

    def add_run(text):
        run = p.add_run(text)
        run.font.name = 'Arial'
        run.font.size = Pt(15)
        run.font.color.rgb = RGBColor(0, 0, 0)

    blank = "（　）"
    if q_type == 1:
        add_run(blank); add_run(str(a)); add_run(blank)
    else:
        add_run(str(a)); add_run(blank); add_run(str(b))


# ── 树状图 ───────────────────────────────────────────────

def _write_tree_lines(cell, lines):
    for p in cell.paragraphs:
        for r in p.runs:
            r.text = ''
    while len(cell.paragraphs) < len(lines):
        cell.add_paragraph()

    for i, line in enumerate(lines):
        p = cell.paragraphs[i]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        for r in p.runs:
            r.text = ''
        run = p.add_run(line)
        run.font.size = Pt(11)
        run.font.name = 'Consolas'
        _set_east_asia(run, 'Consolas')


def write_decompose_tree(cell, total, part1):
    _write_tree_lines(cell, [
        f"{total:^9}",
        "   / \\   ",
        f"   {part1} (  )",
    ])


def write_compose_tree(cell, p1, p2):
    _write_tree_lines(cell, [
        f"  {p1}   {p2}  ",
        "   \\ /   ",
        "  (   )  ",
    ])
