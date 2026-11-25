"""从 data/ 下的已核验笔记里解析词表 → {词: 拼音}。

规则：
- 只读 status=已核验 的 .md 文件（pinyin_notes / kewen_notes / gushi_notes 下）
- 匹配「汉字（拼音）」全角括号，拼音音节数必须等于汉字数
- 首次出现为准（同一个词的不同读音各笔记可能不一致）
"""

from __future__ import annotations

import re
from pathlib import Path


DATA_DIR = Path(__file__).parent / 'data'

_WORD_RE = re.compile(
    r'([一-鿿]{1,6})'
    r'（'
    r'([a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü·\-\s]+)'
    r'）'
)


def _iter_notes():
    """读 data/ 下 pinyin_notes / kewen_notes / gushi_notes 里的所有 .md。

    已核验 / 待核验都读取：
    - 内容本身是孩子学过的东西，待核验也是「已学范围」
    - 读是只读，不涉及修改，和 CLAUDE memory 的「不改已核验」不冲突
    - 首次出现为准（见 load_word_pinyin），已核验按字典序排在前面影响不大
    """
    for sub in ('pinyin_notes', 'kewen_notes', 'gushi_notes'):
        d = DATA_DIR / sub
        if not d.exists():
            continue
        for p in sorted(d.glob('*.md')):
            try:
                text = p.read_text(encoding='utf-8')
            except OSError:
                continue
            yield p, text


def load_word_pinyin() -> dict:
    vocab: dict = {}
    for _p, text in _iter_notes():
        for m in _WORD_RE.finditer(text):
            hanzi = m.group(1)
            pinyin = re.sub(r'\s+', ' ', m.group(2).strip())
            parts = pinyin.split(' ')
            if len(parts) != len(hanzi):
                continue
            vocab.setdefault(hanzi, pinyin)
    return vocab


if __name__ == '__main__':
    v = load_word_pinyin()
    print(f'共 {len(v)} 个词：')
    for w, p in list(v.items())[:30]:
        print(f'  {w} → {p}')
