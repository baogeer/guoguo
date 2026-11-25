"""幼儿园大班短文生成器（agno + DeepSeek V4 版，参考 ai_content_translate_fr_agent.py 的写法）。

网关：https://gate.aidingqing.com  （apifox 分享的 OpenAI-兼容代理）
模型：q-deepseek-v4-pro（创作质量更好；可通过 .env 的 DEEPSEEK_MODEL 换 flash）

- 输入：data/ 已核验+待核验笔记提取的词表，当「孩子已学范围」喂 AI
- 输出 JSON：{"title": "xxx", "0": "第一句", "1": "第二句", ...}
- 失败自动重试 + 清理代码块；无中文 / 格式错 / 段数不对都会触发重试
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.openai.like import OpenAILike

from .article import annotate
from .data_loader import load_word_pinyin


load_dotenv(Path(__file__).resolve().parents[2] / '.env')


# ── 配置 ─────────────────────────────────────────────────

API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://gate.aidingqing.com/v1')
MODEL = os.getenv('DEEPSEEK_MODEL', 'q-deepseek-v4-pro')


# ── 词表 ────────────────────────────────────────────────

_VOCAB = load_word_pinyin()
_PRIORITY_WORDS = sorted(_VOCAB.keys(), key=lambda w: (-len(w), w))[:180]

_SEEDS = [
    '一次家里的小意外', '和小动物交朋友', '晚上看月亮', '去山坡上玩',
    '帮家人做事', '买水果', '发现一个小秘密', '影子跟着我',
    '下雨天的趣事', '和小伙伴分享东西',
]


# ── Prompt 构造 ─────────────────────────────────────────

def _build_user_prompt(target_lines: int, seed: str, vocab_hint: str) -> str:
    sample_keys = ', '.join(f'"{i}": "第{i + 1}句"' for i in range(target_lines))
    return (
        f'请为幼儿园大班（5~6 岁）孩子写一篇小故事，主题方向：{seed}。\n\n'
        f'## 要求\n'
        f'1. 全文严格 {target_lines} 句，每句 10~12 个汉字（不含标点），\n'
        f'   每句必须用「。」「！」「？」结尾，不要用省略号或长句子\n'
        f'2. 第一人称「我」，至少一处对白\n'
        f'3. 有画面感、带小转折或温馨结尾，口吻像米小圈讲故事\n'
        f'4. 多用这些孩子学过的词（主要名词/动词从这里挑）：\n'
        f'   {vocab_hint}\n'
        f'5. 连接词可以用「我/你/的/了/是/就/也/和/又/很」等基础字\n'
        f'6. 口语化、孩子气\n\n'
        f'## 输出格式（严格）\n'
        f'只输出一个 JSON 对象，不要加解释、代码块或任何前后缀。\n'
        f'格式：{{"title": "4~6 字标题", {sample_keys}}}\n'
        f'- 必须恰好 {target_lines} 个数字 key，从 "0" 连续编号到 "{target_lines - 1}"\n'
        f'- 一个 key 对应一句，不要拆分或合并\n'
        f'- 每句以「。」「！」「？」之一结尾\n'
    )


# ── 生成器类 ─────────────────────────────────────────────

class ArticleGenerator:
    """幼儿园大班短文生成器（agno + DeepSeek V4）。"""

    INSTRUCTIONS = (
        '你是一位幼儿园大班的语文老师，擅长用孩子学过的词语编生动有趣的短故事，'
        '风格参考《米小圈上学记》：第一人称、带对白、有小意外或温馨互动，'
        '让 5~6 岁小朋友愿意主动读下去。'
        '\n\n'
        '## 严格的输出要求\n'
        '- 只输出 JSON 对象，不要任何解释、Markdown 代码块、前后缀文字。\n'
        '- JSON 必须包含 "title"（4~6 字标题）和若干数字 key（"0","1","2"...）。\n'
        '- 每个数字 key 的 value 是一句话，10~18 字，口语化。\n'
        '- 数字 key 必须从 "0" 开始连续编号，不能跳号。\n'
        '- 正文中不要出现换行符或 Markdown 符号。\n'
    )

    def __init__(self):
        if not API_KEY:
            raise RuntimeError(
                '缺少 DEEPSEEK_API_KEY。请在项目根目录的 .env 里设置：\n'
                '  DEEPSEEK_API_KEY=sk-xxxxxxxx\n'
                '（参考 .env.example）'
            )
        self.model_id = MODEL
        self.api_key = API_KEY
        self.base_url = BASE_URL
        self._agent = self._build_agent()

    def _build_model(self) -> OpenAILike:
        return OpenAILike(
            id=self.model_id,
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def _build_agent(self) -> Agent:
        return Agent(
            name='KindergartenStoryWriter',
            model=self._build_model(),
            instructions=self.INSTRUCTIONS,
            markdown=False,
        )

    # ── 响应清理与解析 ──────────────────────────────────

    @staticmethod
    def _clean_json(content: str) -> str:
        """去掉代码块标记，提取第一个 { 到最后一个 } 之间的 JSON。"""
        content = (content or '').strip()
        content = re.sub(r'```[a-zA-Z]*', '', content).replace('```', '')
        content = content.strip()
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1 and end > start:
            content = content[start:end + 1]
        return content

    @staticmethod
    def _parse_response(content: str) -> Tuple[str, List[str]]:
        raw = ArticleGenerator._clean_json(content)
        if not raw:
            raise ValueError(f'AI 返回空内容：{content!r}')
        data = json.loads(raw)
        title = str(data.get('title', '')).strip() or '小故事'

        # 收集数字 key 的句子
        numeric_items = []
        for k, v in data.items():
            if k == 'title':
                continue
            try:
                numeric_items.append((int(k), str(v).strip()))
            except (TypeError, ValueError):
                continue
        if not numeric_items:
            raise ValueError(f'AI 没有返回正文句子：{data}')
        numeric_items.sort(key=lambda x: x[0])
        lines = [v for _, v in numeric_items if v]
        if not lines:
            raise ValueError('所有句子都是空的')
        return title, lines

    # ── 对外 API ─────────────────────────────────────────

    def generate(self, max_retries: int = 4) -> Dict[str, Any]:
        """生成一篇短文，返回 {'title', 'lines', 'status'}。"""
        for attempt in range(max_retries):
            try:
                target_lines = 10
                words = list(_PRIORITY_WORDS)
                random.shuffle(words)
                vocab_hint = '、'.join(words[:80])
                seed = random.choice(_SEEDS)
                prompt = _build_user_prompt(target_lines, seed, vocab_hint)

                response = self._agent.run(prompt)
                content = getattr(response, 'content', None) or ''
                title, lines = self._parse_response(content)

                # 校验：每句不能夹带 Markdown 或引号围栏
                lines = [re.sub(r'\s+', '', ln) for ln in lines if ln.strip()]
                if not lines:
                    raise ValueError('清理后无正文')

                return {'title': title, 'lines': lines, 'status': 1}
            except Exception as e:
                wait = 2 ** attempt
                print(f'[AI] 第 {attempt + 1} 次尝试失败：{e}；{wait}s 后重试')
                time.sleep(wait)

        return {'title': None, 'lines': None, 'status': 0}


# ── 入口函数（保持与原 generate_article 接口兼容）────

def generate_article_ai():
    """返回 (标题, [[(字, 拼音)]...])。失败抛 RuntimeError 让 main 降级。"""
    gen = ArticleGenerator()
    result = gen.generate()
    if not result['status']:
        raise RuntimeError('AI 多次重试后仍失败')
    body = '\n'.join(result['lines'])
    return result['title'], annotate(body)


if __name__ == '__main__':
    gen = ArticleGenerator()
    r = gen.generate()
    print(json.dumps(r, ensure_ascii=False, indent=2))
