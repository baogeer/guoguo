"""题目渲染：将题目数据写入 Word 单元格/段落。"""

from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn, nsdecls
from docx.oxml import OxmlElement, parse_xml
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


# ── 应用题 ───────────────────────────────────────────────

def _ruby_xml(char, pinyin, hanzi_pt=11, pinyin_pt=5):
    """生成一个 <w:r><w:ruby>...</w:ruby></w:r> 元素（汉字上标拼音）。"""
    hps = int(hanzi_pt * 2)   # half-point size
    pps = int(pinyin_pt * 2)
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    xml = (
        f'<w:r {ns}>'
        f'<w:ruby>'
        f'<w:rubyPr>'
        f'<w:rubyAlign w:val="center"/>'
        f'<w:hps w:val="{pps}"/>'
        f'<w:hpsRaise w:val="{hps}"/>'
        f'<w:hpsBaseText w:val="{hps}"/>'
        f'<w:lid w:val="zh-CN"/>'
        f'</w:rubyPr>'
        f'<w:rt>'
        f'<w:r><w:rPr>'
        f'<w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
        f'<w:sz w:val="{pps}"/>'
        f'</w:rPr>'
        f'<w:t>{pinyin}</w:t></w:r>'
        f'</w:rt>'
        f'<w:rubyBase>'
        f'<w:r><w:rPr>'
        f'<w:rFonts w:eastAsia="宋体"/>'
        f'<w:sz w:val="{hps}"/>'
        f'</w:rPr>'
        f'<w:t>{char}</w:t></w:r>'
        f'</w:rubyBase>'
        f'</w:ruby>'
        f'</w:r>'
    )
    return parse_xml(xml)


def _is_hanzi(ch):
    return '一' <= ch <= '鿿'


def _add_pinyin_text(paragraph, text, hanzi_pt=11, pinyin_pt=5):
    """把一段中文文字加到 paragraph 里，汉字上方标拼音，非汉字直接写。"""
    from pypinyin import lazy_pinyin, Style
    from src.chinese.article import WORD_PINYIN as _WP

    # 把文字切成 (汉字段, 非汉字段) 交替的 chunks
    chunks = []
    buf = ''
    is_hz = None
    for ch in text:
        cur = _is_hanzi(ch)
        if is_hz is not None and cur != is_hz:
            chunks.append((is_hz, buf))
            buf = ''
        buf += ch
        is_hz = cur
    if buf:
        chunks.append((is_hz, buf))

    for hz, chunk in chunks:
        if not hz:
            run = paragraph.add_run(chunk)
            run.font.size = Pt(hanzi_pt)
            run.font.name = '宋体'
            _set_east_asia(run, '宋体')
        else:
            # 对汉字段做最长词匹配拼音
            pys = []
            i = 0
            while i < len(chunk):
                matched = False
                for L in range(min(6, len(chunk) - i), 1, -1):
                    cand = chunk[i:i + L]
                    if cand in _WP:
                        parts = _WP[cand].split(' ')
                        if len(parts) == L:
                            pys.extend(zip(cand, parts))
                            i += L
                            matched = True
                            break
                if not matched:
                    ch = chunk[i]
                    py = lazy_pinyin(ch, style=Style.TONE)[0]
                    pys.append((ch, py))
                    i += 1
            for ch, py in pys:
                paragraph._p.append(_ruby_xml(ch, py, hanzi_pt, pinyin_pt))


def add_word_problem_question(cell, text, op, a, b):
    """把一道应用题写进单元格：带拼音的题目文字。"""
    from .generators import _wp_fill_template

    filled = _wp_fill_template(text, a, b)

    for p in cell.paragraphs:
        for r in p.runs:
            r.text = ''

    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    _add_pinyin_text(p, filled, hanzi_pt=11, pinyin_pt=5)
