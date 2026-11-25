"""幼儿园大班短文生成器（米小圈故事风格）。

- 词汇拼音从 data/ 已核验笔记动态加载（data_loader.load_word_pinyin）
- 故事模板里的「内容词」（人物/动物/食物/地点）都从笔记里的词表里挑，
  连接词和基础字用 pypinyin 兜底；变调「不 / 一」由 SANDHI 覆盖
- 每个故事 100~160 字，带对白、有起承转合，一页能放下
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Dict

from pypinyin import lazy_pinyin, Style

from .data_loader import load_word_pinyin


# ── 词级拼音：数据优先，变调兜底 ─────────────────────────

_DATA_WORDS = load_word_pinyin()

_SANDHI = {
    '不用': 'bú yòng', '不要': 'bú yào', '不好': 'bù hǎo',
    '不会': 'bú huì', '不是': 'bú shì', '不去': 'bú qù',
    '不来': 'bù lái', '不哭': 'bù kū', '不怕': 'bú pà',
    '不到': 'bú dào', '不行': 'bù xíng', '不动': 'bú dòng',
    '一起': 'yì qǐ', '一条': 'yì tiáo', '一只': 'yì zhī',
    '一个': 'yí gè', '一朵': 'yì duǒ', '一天': 'yì tiān',
    '一片': 'yí piàn', '一家': 'yì jiā', '一棵': 'yì kē',
    '一声': 'yì shēng', '一边': 'yì biān', '一回': 'yì huí',
    '一次': 'yí cì', '一半': 'yí bàn', '一下': 'yí xià',
    '一口': 'yì kǒu', '一大口': 'yí dà kǒu',
    '一本': 'yì běn', '一杯': 'yì bēi',
}

WORD_PINYIN: Dict[str, str] = dict(_DATA_WORDS)
for _w, _p in _SANDHI.items():
    WORD_PINYIN.setdefault(_w, _p)


# ── 词池（全部存在于 _DATA_WORDS 中） ─────────────────────

def _only_in_data(words: List[str]) -> List[str]:
    ok, miss = [], []
    for w in words:
        (ok if w in _DATA_WORDS else miss).append(w)
    if miss:
        print(f'[article] 跳过未在 data/ 笔记里出现的词：{miss}')
    return ok


PEOPLE_ADULT = _only_in_data(['爸爸', '妈妈', '外婆', '伯父', '姑姑'])
PEOPLE_ALL = _only_in_data(['爸爸', '妈妈', '哥哥', '外婆', '伯父', '姑姑'])
ANIMALS = _only_in_data(['小兔', '小猪', '老虎', '猫咪', '母鸡', '小黑狗',
                         '马儿', '驴子', '兔子'])
ANIMALS_FRIEND = _only_in_data(['小猪', '猫咪', '母鸡', '驴子', '马儿'])
FRUITS = _only_in_data(['西瓜', '葡萄', '萝卜', '苦瓜', '大米'])


# ── 故事模板 ─────────────────────────────────────────────

@dataclass
class Story:
    titles: List[str]
    body: str
    slots: Dict[str, List[str]] = field(default_factory=dict)
    uniques: List[List[str]] = field(default_factory=list)


STORIES: List[Story] = [

    Story(
        titles=['一个大西瓜', '抱回大西瓜', '一人一块'],
        body=(
            '今天中午，{p1}从外面抱回一个大{food}。\n'
            '「哇！这么大一个！」我和{p2}一起叫起来。\n'
            '{p1}笑着说：「来，切开，一人一块。」\n'
            '我咬了一大口，水水的，甜甜的，真好吃！\n'
            '{p2}也吃得眯起了眼睛。\n'
            '一家人在一起，{food}都变得更甜了。'
        ),
        slots={'p1': PEOPLE_ADULT, 'p2': PEOPLE_ADULT, 'food': FRUITS},
        uniques=[['p1', 'p2']],
    ),

    Story(
        titles=['影子小黑狗', '我的好朋友影子', '跟着我的小黑狗'],
        body=(
            '今天早上，太阳出来了，我跑出家门去玩。\n'
            '一低头，呀！脚下有个黑黑的东西！\n'
            '我走，它也走；我跑，它也跑。\n'
            '妈妈笑着说：「那是你的影子呀！」\n'
            '「影子就像一只小黑狗，天天陪着你。」\n'
            '哈哈，原来影子，是我的好朋友！'
        ),
    ),

    Story(
        titles=['老虎的咖啡店', '一杯苦咖啡', '小兔喝咖啡'],
        body=(
            '山坡上，老虎开了一家小小的咖啡店。\n'
            '一天，小兔走进来，笑着说：「我要一杯咖啡！」\n'
            '老虎端上一杯：「请慢用！」\n'
            '小兔喝了一口，咕嘟嘟——哎呀，苦苦的！\n'
            '「老虎哥哥，你的咖啡有点苦呀。」\n'
            '老虎哈哈大笑：「这就叫咖啡呀，小兔！」\n'
            '小兔捂着嘴，笑弯了腰。'
        ),
    ),

    Story(
        titles=['弯弯的月儿船', '小小的船', '想坐月亮船'],
        body=(
            '晚上，{p1}带我到院子里看月亮。\n'
            '月儿弯弯的，像一只小小的船。\n'
            '我说：「{p1}，我也想坐上去！」\n'
            '{p1}笑着说：「等你长大，就能飞上去。」\n'
            '蓝蓝的天上，星星闪闪地眨眼。\n'
            '我在心里悄悄地想：\n'
            '等我长大，一定坐上小小的船，去看星星！'
        ),
        slots={'p1': PEOPLE_ADULT},
    ),

    Story(
        titles=['跑丢了葡萄', '摔一跤', '手里的水果'],
        body=(
            '今天下午，{p1}给了我一大串{food}。\n'
            '我抱着{food}，飞快地跑去找{p2}。\n'
            '跑着跑着，「咚」地一声，我摔了一跤！\n'
            '{food}骨碌碌地滚远了。\n'
            '{p1}赶紧跑过来：「哎呀，摔疼了吗？」\n'
            '我爬起来，摸摸鼻子说：「{food}先跑了！」\n'
            '{p1}和{p2}都笑弯了腰。'
        ),
        slots={'p1': PEOPLE_ADULT, 'p2': PEOPLE_ALL, 'food': FRUITS},
        uniques=[['p1', 'p2']],
    ),

    Story(
        titles=['我是小帮手', '我也会思考', '一家人'],
        body=(
            '妈妈在做工，爸爸在读书。\n'
            '我也想帮忙，就跑过去问：「我能做什么？」\n'
            '妈妈笑着说：「你会什么呀？」\n'
            '我挺起小胸脯：「我会思考！」\n'
            '爸爸也笑了：「那你帮爸爸想一想，\n'
            '今天我们吃什么？」\n'
            '我歪着头想了半天：「吃{food}！」\n'
            '一家人一起哈哈大笑。我真是个小帮手！'
        ),
        slots={'food': FRUITS},
    ),

    Story(
        titles=['小兔找吃的', '山坡上的大萝卜', '好东西要分享'],
        body=(
            '小兔的肚子饿得咕咕叫，它跑到山坡上找吃的。\n'
            '走呀走，它看见了一个大大的{food}。\n'
            '小兔高兴极了，抱起{food}就往家跑。\n'
            '到家后，它敲开{animal}的门：\n'
            '「{animal}，我们一起吃{food}！」\n'
            '两个好朋友坐在一起，吃得真香！\n'
            '小兔说：「好东西呀，就要和朋友一起分享。」'
        ),
        slots={'food': FRUITS, 'animal': ANIMALS_FRIEND},
    ),

    Story(
        titles=['用手又用脑', '一条心', '我要做玩具'],
        body=(
            '{p1}会做工，{p2}会思考。\n'
            '我呢？我爱读书，也爱玩耍。\n'
            '一家人在一起，就像一条心。\n'
            '妈妈常常说：「用手又用脑，才能有创造。」\n'
            '我点点头，把这句话悄悄记在心里。\n'
            '明天，我要和{p3}一起，\n'
            '用双手和大脑，做一个漂亮的小玩具！'
        ),
        slots={'p1': PEOPLE_ALL, 'p2': PEOPLE_ALL, 'p3': PEOPLE_ALL},
        uniques=[['p1', 'p2', 'p3']],
    ),

    Story(
        titles=['猫咪的秘密', '偷鱼的猫咪', '咪呜咪呜'],
        body=(
            '{p1}的家里，有一只胖胖的猫咪。\n'
            '一天，妈妈做好了饭，叫我去洗手。\n'
            '回来一看——哎呀，桌上的鱼不见了！\n'
            '猫咪蹲在门口，咪呜咪呜地叫。\n'
            '它的嘴边还沾着一小片鱼鳞呢。\n'
            '妈妈笑着说：「这个小秘密，被我们发现啦！」\n'
            '猫咪低下头，不好意思地跑开了。'
        ),
        slots={'p1': PEOPLE_ADULT},
    ),

    Story(
        titles=['哥哥的图书', '一本好书', '我也爱读书'],
        body=(
            '哥哥坐在桌前读书，读得特别认真。\n'
            '我悄悄地走过去，搬了一本图书坐在他旁边。\n'
            '哥哥笑了：「你能看懂吗？」\n'
            '我说：「我看图！」\n'
            '我们一起看了一本关于{animal}的书。\n'
            '书里的{animal}，又可爱又聪明。\n'
            '哥哥摸摸我的头：「你爱动脑筋，真棒！」\n'
            '我心里美滋滋的，比吃了{food}还甜。'
        ),
        slots={'animal': ANIMALS, 'food': FRUITS},
    ),
]


# ── 填槽 ─────────────────────────────────────────────────

def _fill_slots(story: Story) -> Dict[str, str]:
    picks: Dict[str, str] = {}
    locked = set()
    for group in story.uniques:
        pool = story.slots[group[0]]
        used = set()
        for slot in group:
            avail = [x for x in story.slots[slot] if x not in used]
            if not avail:
                avail = story.slots[slot]
            pick = random.choice(avail)
            picks[slot] = pick
            used.add(pick)
            locked.add(slot)
    for slot, pool in story.slots.items():
        if slot in locked:
            continue
        picks[slot] = random.choice(pool)
    return picks


# ── 标注拼音 ─────────────────────────────────────────────

_HANZI_RE_CHAR = lambda ch: '一' <= ch <= '鿿'


def _pinyin_chunk(chunk: str) -> List[tuple]:
    """对纯汉字段做最长匹配：先查 WORD_PINYIN，不中再逐字 pypinyin。"""
    out = []
    i = 0
    while i < len(chunk):
        matched = 0
        for L in range(min(6, len(chunk) - i), 1, -1):
            cand = chunk[i:i + L]
            if cand in WORD_PINYIN:
                parts = WORD_PINYIN[cand].split(' ')
                if len(parts) == L:
                    for c, p in zip(cand, parts):
                        out.append((c, p))
                    matched = L
                    break
        if matched == 0:
            ch = chunk[i]
            if ch in WORD_PINYIN:
                out.append((ch, WORD_PINYIN[ch]))
            else:
                p = lazy_pinyin(ch, style=Style.TONE)[0]
                out.append((ch, p))
            matched = 1
        i += matched
    return out


def annotate(text: str) -> List[List[tuple]]:
    lines = []
    for raw in text.split('\n'):
        units: List[tuple] = []
        buf = ''
        for ch in raw:
            if _HANZI_RE_CHAR(ch):
                buf += ch
            else:
                if buf:
                    units.extend(_pinyin_chunk(buf))
                    buf = ''
                if ch and not ch.isspace():
                    units.append((ch, ''))
        if buf:
            units.extend(_pinyin_chunk(buf))
        lines.append(units)
    return lines


# ── 对外入口 ─────────────────────────────────────────────

def generate_article():
    story = random.choice(STORIES)
    title = random.choice(story.titles)
    picks = _fill_slots(story) if story.slots else {}
    body = story.body.format(**picks) if picks else story.body
    return title, annotate(body)
