"""
LLM client for bili_summary.

Wraps the openai SDK to call an OpenAI-compatible endpoint (default: opencode go).
Reads credentials and model from environment:
    OPENCODE_BASE_URL   e.g. https://api.opencode.ai/v1
    OPENCODE_API_KEY    user's API key
    LLM_MODEL           e.g. gpt-4o-mini

Public surface:
    LLMClient().summarize(transcript_text, meta, on_progress=None) -> dict

Handles:
- Token counting via tiktoken
- Transcript truncation when too long
- Map/reduce chunking for >24k-token transcripts
- Retries with exponential backoff (1s/3s/9s)
- JSON-mode fallback (drops response_format if the proxy strips it)
- Lightweight schema validation (no jsonschema)
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Callable, Optional

# openai SDK 2.31.0 is already installed.
import openai
import tiktoken

# httpx ships transitively with openai SDK; used for raw Anthropic HTTP calls.
import httpx


SYSTEM_PROMPT = """你是 bili_summary 的视频内容总结助手，专精于 B 站长视频的结构化总结。

# 规则
1. 输出必须是单个 JSON 对象，严格遵循下方 schema，不要任何 markdown 代码块标记或额外说明文字。
2. 使用简体中文（仅 eyebrow 等标签字段可使用英文）。
3. 忠于原文：可以引用或改写，不要编造事实、数据、引语。若某章节无源材料支撑，输出 null，不要硬填。
4. 字段长度硬上限（renderer 也会二次截断）：每个 string ≤ 200 字符；每条 bullet ≤ 80 字符；超长用 … 收尾。
5. `infographic.cards` 必须恰好 5-9 张；其中恰好一张 `is_hero: true`，其余省略该字段。
6. `sections` 给 4-8 个；每个 section 的 body 是一段 ≤ 280 字符的概述 + 3-6 条 bullets。
7. `pull_quote` 字段必须来自转录原文，是最值得记住的一两句话。
8. `timestamp_index` 仅在转录有清晰主题分段时输出，否则 null。
9. `quotes` 给出 5-12 条金句，要短、有力、可引用。

# 标题长度约束（重要）
- `cover.display_title` ≤ 12 个中文字符
- `sections[i].title` ≤ 12 个中文字符 —— 标题应精准概括，过长的内容放入 body 和 bullets
- `infographic.cards[].title` ≤ 10 个中文字符
- `infographic.cards[].bullets[]` ≤ 30 个中文字符每条

# 字段说明（rendered as-is, missing fields skipped gracefully）
- meta: 视频元数据（沿用输入，补充你认为有用的字段）
- cover: 封面图字段（display_title ≤ 12 字；pull_quote ≤ 60 字）
- infographic: 信息图（cards: list，每张 number/title/bullets）
- intro: 引言段落（paragraph ≤ 280 字）
- sections: 主章节列表
- pro_tips: 临场技巧/小贴士列表（仅当视频明确给出可操作建议时提供，不要编造通用建议）
- money_map: 花钱建议（status ∈ 推荐/不建议/看情况）
- quotes: 金句数组
- timestamp_index: 时间戳索引
- closing: 免责声明与署名
"""

USER_TEMPLATE = """=== VIDEO METADATA ===
标题: {title}
UP主: {uploader}
时长: {duration_label}
播放量: {view}
标签: {tags}

=== TRANSCRIPT ({n_segments} 段, {n_chars} 字符) ===
{transcript}

=== OUTPUT SCHEMA REMINDER ===
Return JSON with these top-level keys (any missing/null is allowed):
meta, cover, infographic, intro, sections, pro_tips, money_map,
quotes, timestamp_index, closing.

Required for the renderer to work:
- cover.display_title  (≤ 12 chars Chinese)
- cover.pull_quote    (≤ 60 chars, verbatim from transcript)
- cover.stats         (exactly 3 entries, each with num/unit/label/sub)
- infographic.cards   (5-9 entries, exactly one with is_hero: true)
- timestamp_index.rows  —— 每行格式: {{"range": "00:00-05:00", "topic": "章节标题"}}，range 是时间范围字符串，topic 是主题名

Prefer null over bad data. Renderers tolerate missing optional sections.
"""

CHUNK_SUMMARIZE_PROMPT = """你是 bili_summary 的预处理助手。下方是一段视频转录的中间片段，请你提炼出这段中最有价值的 3-5 条要点（每条 ≤ 80 字符中文）。输出必须是 JSON: {{"bullets": ["...", "..."]}}。

=== TRANSCRIPT CHUNK ===
{chunk}
"""

ProgressCb = Optional[Callable[[str, float], None]]


class LLMClient:
    MAX_TRANSCRIPT_TOKENS = 24_000
    CHUNK_TOKENS = 6_000
    CHARS_PER_TOKEN = 1.5  # conservative for Chinese

    CONFIG_FILE = Path(__file__).parent.parent / 'llm_config.json'

    def __init__(self) -> None:
        # Priority: env var > llm_config.json > hardcoded fallback
        self.base_url = (
            os.environ.get('OPENCODE_BASE_URL')
            or self._cfg('base_url')
            or ''
        ).rstrip('/')
        self.api_key = (
            os.environ.get('OPENCODE_API_KEY')
            or self._cfg('api_key')
            or ''
        )
        self.model = (
            os.environ.get('LLM_MODEL')
            or self._cfg('model')
            or 'gpt-4o-mini'
        )
        # Protocol selector: 'openai' (/v1/chat/completions) | 'anthropic' (/v1/messages)
        proto = (
            os.environ.get('LLM_PROTOCOL')
            or self._cfg('protocol')
            or 'openai'
        ).strip().lower()
        self.protocol = 'anthropic' if proto in ('anthropic', 'claude', 'messages') else 'openai'
        self._client: Optional[openai.OpenAI] = None
        self._enc = None

    @classmethod
    def _cfg(cls, key: str) -> str | None:
        """Read a key from llm_config.json (project root). Returns None if absent."""
        if not cls.CONFIG_FILE.exists():
            return None
        try:
            data = json.loads(cls.CONFIG_FILE.read_text(encoding='utf-8'))
            val = data.get(key)
            return str(val).strip() if val else None
        except Exception:
            return None

    # ---- public ----
    def summarize(
        self,
        transcript_text: str,
        meta: dict,
        on_progress: ProgressCb = None,
    ) -> dict:
        self._require_env()

        if on_progress:
            on_progress(f'调用 LLM ({self.model})...', 0.55)

        n_tokens = self._count_tokens(transcript_text)
        if on_progress:
            on_progress(f'检测到 {n_tokens} tokens', 0.58)

        if n_tokens > self.MAX_TRANSCRIPT_TOKENS:
            if on_progress:
                on_progress('需要分段摘要 (map/reduce)...', 0.60)
            transcript_text = self._reduce_via_chunking(
                transcript_text, on_progress,
            )
            if on_progress:
                on_progress('生成结构化总结...', 0.65)

        messages = self._build_messages(transcript_text, meta)

        if on_progress:
            on_progress('生成结构化总结...', 0.66)

        raw = self._call_llm(messages, on_progress)

        if on_progress:
            on_progress('解析 LLM 输出...', 0.68)

        data = self._parse_json(raw)
        data = self._validate(data, meta)

        if on_progress:
            on_progress(
                f'OK: LLM 总结 {len(json.dumps(data, ensure_ascii=False))} 字符',
                0.70,
            )

        return data

    # ---- env / setup ----
    def _require_env(self) -> None:
        missing = []
        if not self.base_url:
            missing.append('OPENCODE_BASE_URL')
        if not self.api_key:
            missing.append('OPENCODE_API_KEY')
        if not self.model:
            missing.append('LLM_MODEL')
        if missing:
            hint = (
                '（推荐使用 opencode go 套餐的 OpenAI 兼容端点；'
                '若使用 Anthropic 原生协议，请在 llm_config.json 设 '
                '"protocol": "anthropic"）'
            )
            raise RuntimeError(
                '请设置环境变量：' + ' / '.join(missing) + ' ' + hint
            )

    def _openai_client(self) -> openai.OpenAI:
        if self._client is None:
            self._client = openai.OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )
        return self._client

    def _encoding(self):
        if self._enc is None:
            try:
                self._enc = tiktoken.encoding_for_model(self.model)
            except KeyError:
                self._enc = tiktoken.get_encoding('cl100k_base')
        return self._enc

    def _count_tokens(self, text: str) -> int:
        return len(self._encoding().encode(text))

    # ---- prompt ----
    def _build_messages(self, transcript: str, meta: dict) -> list:
        user = USER_TEMPLATE.format(
            title=meta.get('title', ''),
            uploader=meta.get('uploader', ''),
            duration_label=meta.get('duration_label', ''),
            view=meta.get('view', ''),
            tags='、'.join(meta.get('tags', []) or []) or '（无）',
            n_segments=meta.get('n_segments', '?'),
            n_chars=len(transcript),
            transcript=transcript,
        )
        return [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': user},
        ]

    # ---- chunking ----
    def _reduce_via_chunking(
        self, transcript: str, on_progress: ProgressCb,
    ) -> str:
        """Map/reduce: chunk transcript, summarize each, concat bullets."""
        # Split into roughly equal chunks by characters; finer than by tokens
        # but conservative for CJK (each char ~ 1 token).
        chars_per_chunk = int(self.CHUNK_TOKENS * self.CHARS_PER_TOKEN)
        chunks = self._split_text(transcript, chars_per_chunk)
        if on_progress:
            on_progress(
                f'需要分段摘要 ({len(chunks)} 段)...', 0.62,
            )

        all_bullets: list[str] = []
        chunk_warnings: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            if on_progress:
                on_progress(
                    f'分段摘要 {i}/{len(chunks)}...', 0.62 + 0.02 * i,
                )
            try:
                payload = self._call_chunk(chunk)
                data = json.loads(payload)
                bullets = data.get('bullets', []) or []
            except openai.AuthenticationError as e:
                # Auth failures are fatal — bubble up so the user fixes creds.
                raise RuntimeError(
                    f'鉴权失败（请检查 OPENCODE_API_KEY 是否正确）: {e}'
                ) from e
            except Exception as e:  # noqa: BLE001
                # Transient (network / rate-limit / parse) — record and skip.
                # This keeps a partial summary usable when 1 of N chunks fails.
                chunk_warnings.append(f'#{i}: {type(e).__name__}: {e}')
                if on_progress:
                    on_progress(
                        f'⚠ 分段 {i}/{len(chunks)} 失败，跳过: {type(e).__name__}',
                        0.62 + 0.02 * i,
                    )
                bullets = []
            all_bullets.extend(bullets)

        if on_progress and chunk_warnings:
            on_progress(
                f'⚠ 共 {len(chunk_warnings)}/{len(chunks)} 段失败: '
                + '; '.join(chunk_warnings[:3]),
                0.66,
            )

        # Dedupe (case-insensitive, by first sentence).
        seen, unique = set(), []
        for b in all_bullets:
            key = b.strip().split('。')[0].lower()[:40]
            if key and key not in seen:
                seen.add(key)
                unique.append(b)
        unique = unique[:150]

        joined = '\n'.join(f'· {b}' for b in unique)
        return joined

    @staticmethod
    def _split_text(text: str, chunk_chars: int) -> list[str]:
        if len(text) <= chunk_chars:
            return [text]
        chunks = []
        i = 0
        while i < len(text):
            end = min(i + chunk_chars, len(text))
            # try to break at a newline
            if end < len(text):
                nl = text.rfind('\n', i + chunk_chars // 2, end)
                if nl > i:
                    end = nl
            chunks.append(text[i:end].strip())
            i = end
        return [c for c in chunks if c]

    def _call_chunk(self, chunk: str) -> str:
        """Per-chunk summarization dispatch (used by map/reduce).
        Returns the raw JSON-string content (no validation here)."""
        user_content = CHUNK_SUMMARIZE_PROMPT.format(chunk=chunk)
        if self.protocol == 'anthropic':
            # Anthropic: no system prompt needed, but we still inject one
            # for chunk to encourage JSON-only output.
            return self._call_anthropic([{
                'role': 'user', 'content': user_content,
            }], on_progress=None)
        # OpenAI default
        client = self._openai_client()
        resp = client.chat.completions.create(
            model=self.model,
            messages=[{'role': 'user', 'content': user_content}],
            response_format={'type': 'json_object'},
            temperature=0.2,
            max_tokens=600,
        )
        return resp.choices[0].message.content or '{}'

    # ---- call with retries ----
    def _call_llm(
        self, messages: list, on_progress: ProgressCb,
        use_json_mode: bool = True,
    ) -> str:
        """Dispatcher: delegate to the right protocol implementation,
        retry on transient errors, and validate JSON output."""
        last_err: Optional[Exception] = None
        for attempt in range(3):
            try:
                if self.protocol == 'anthropic':
                    content = self._call_anthropic(messages, on_progress)
                else:
                    content = self._call_openai(
                        messages, on_progress, use_json_mode=use_json_mode,
                    )

                # ---- Shared JSON validation (same for both protocols) ----
                if not content.strip():
                    raise RuntimeError('LLM 返回空内容')
                _raw_stripped = content.strip()
                try:
                    json.loads(_raw_stripped)
                except json.JSONDecodeError:
                    # Try to extract outermost {...} block
                    a, b = _raw_stripped.find('{'), _raw_stripped.rfind('}')
                    if a >= 0 and b > a:
                        try:
                            json.loads(_raw_stripped[a:b + 1])
                            return _raw_stripped[a:b + 1]
                        except json.JSONDecodeError:
                            pass
                    raise RuntimeError(
                        'LLM 输出不是合法 JSON（前 200 字符）: '
                        f'{_raw_stripped[:200]}'
                    )
                return content

            except RuntimeError:
                # JSON parse failure or auth / protocol — try fallback
                if use_json_mode:
                    use_json_mode = False
                    if on_progress:
                        on_progress(
                            'JSON 模式失败，重试...', 0.66,
                        )
                    continue
                if last_err:
                    raise  # already retried with both modes
                raise
            except Exception as e:  # noqa: BLE001
                last_err = e
                if on_progress:
                    on_progress(
                        f'LLM 调用失败，{attempt + 1}/3 重试...', 0.66,
                    )
                time.sleep(1 * (3 ** attempt))

        # Exhausted retries
        if last_err:
            raise RuntimeError(f'LLM 调用失败（已重试 3 次）: {last_err}')
        raise RuntimeError('LLM 调用失败（已重试 3 次）')

    # ---- OpenAI protocol ----
    def _call_openai(
        self, messages: list, on_progress: ProgressCb,
        use_json_mode: bool = True,
    ) -> str:
        last_err: Optional[Exception] = None
        for attempt in range(3):
            try:
                kwargs = dict(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=8192,
                )
                if use_json_mode:
                    kwargs['response_format'] = {'type': 'json_object'}
                resp = self._openai_client().chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ''
            except openai.AuthenticationError as e:
                raise RuntimeError(
                    f'鉴权失败（请检查 OPENCODE_API_KEY 是否正确）: {e}'
                ) from e
            except (openai.RateLimitError, openai.APIStatusError,
                    openai.APIConnectionError) as e:
                last_err = e
                if on_progress:
                    on_progress(
                        f'LLM 调用失败，{attempt + 1}/3 重试...', 0.66,
                    )
                time.sleep(1 * (3 ** attempt))  # 1s, 3s, 9s
            except Exception as e:  # noqa: BLE001
                last_err = e
                time.sleep(1 * (3 ** attempt))
        raise RuntimeError(f'LLM 调用失败（已重试 3 次）: {last_err}')

    # ---- Anthropic protocol (raw HTTP via httpx) ----
    def _call_anthropic(
        self, messages: list, on_progress: ProgressCb,
    ) -> str:
        """POST /v1/messages using Anthropic native format.

        Differences from OpenAI:
        - 'system' must be a top-level field, not a messages entry.
        - Auth via 'x-api-key' header (+ 'anthropic-version').
        - No response_format; we rely on the prompt's JSON instruction.
        """
        # Separate system from user/assistant messages
        system_parts: list[str] = []
        chat_msgs: list[dict] = []
        for m in messages:
            role = m.get('role', '')
            content = m.get('content', '')
            if role == 'system':
                system_parts.append(content)
            else:
                chat_msgs.append({'role': role, 'content': content})

        url = self.base_url.rstrip('/') + '/v1/messages'
        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        }
        payload = {
            'model': self.model,
            'max_tokens': 8192,
            'temperature': 0.3,
            'system': '\n\n'.join(system_parts) if system_parts else '',
            'messages': chat_msgs,
        }

        last_err: Optional[Exception] = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=httpx.Timeout(180.0)) as client:
                    resp = client.post(url, json=payload, headers=headers)
                if resp.status_code == 401:
                    raise RuntimeError(
                        f'Anthropic 鉴权失败（请检查 API Key）: {resp.text[:200]}'
                    )
                if resp.status_code == 429:
                    raise RuntimeError(f'Anthropic 限流: {resp.text[:200]}')
                if resp.status_code >= 500:
                    raise RuntimeError(
                        f'Anthropic 服务端错误 {resp.status_code}: '
                        f'{resp.text[:200]}'
                    )
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f'Anthropic 客户端错误 {resp.status_code}: '
                        f'{resp.text[:200]}'
                    )
                data = resp.json()
                # Anthropic returns {"content": [{"type":"text","text":"..."}, ...]}
                content_blocks = data.get('content') or []
                text_parts = [
                    blk.get('text', '') for blk in content_blocks
                    if isinstance(blk, dict) and blk.get('type') == 'text'
                ]
                content = '\n'.join(text_parts).strip()
                if not content:
                    raise RuntimeError(
                        f'Anthropic 返回空文本内容: {resp.text[:200]}'
                    )
                return content
            except RuntimeError:
                # Auth / protocol errors: surface immediately, don't retry.
                raise
            except Exception as e:  # noqa: BLE001
                last_err = e
                if on_progress:
                    on_progress(
                        f'LLM 调用失败，{attempt + 1}/3 重试...', 0.66,
                    )
                time.sleep(1 * (3 ** attempt))
        raise RuntimeError(f'LLM 调用失败（已重试 3 次）: {last_err}')

    # ---- parse ----
    @staticmethod
    def _parse_json(raw: str) -> dict:
        text = raw.strip()
        # If it already starts with {, try direct parse first (fast path)
        if text.startswith('{'):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        # Strip markdown fences — use greedy match to handle nested braces
        fence = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, re.DOTALL)
        if fence:
            text = fence.group(1)
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        # Fallback: extract outermost {...}
        start, end = text.find('{'), text.rfind('}')
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f'LLM JSON 解析失败: {e}. '
                    f'前 300 字符: {raw[:300]}'
                ) from e
        raise RuntimeError(
            f'LLM 输出中找不到 JSON 对象 (前 200 字符): {raw[:200]}'
        )

    # ---- validate ----
    @staticmethod
    def _validate(data: dict, fallback_meta: dict) -> dict:
        if not isinstance(data, dict):
            raise RuntimeError(f'LLM 输出不是 dict: {type(data).__name__}')

        # meta — always present from pipeline; merge in LLM's additions
        meta = data.get('meta') or {}
        for k, v in fallback_meta.items():
            meta.setdefault(k, v)
        data['meta'] = meta

        # cover
        cover = data.get('cover') or {}
        stats = cover.get('stats') or []
        # Pad stats to exactly 3
        while len(stats) < 3:
            stats.append({
                'num': '—', 'unit': '', 'label': '（未提供）', 'sub': '',
            })
        cover['stats'] = stats[:3]
        data['cover'] = cover

        # infographic
        info = data.get('infographic') or {}
        cards = info.get('cards') or []
        if not isinstance(cards, list):
            cards = []
        # Ensure exactly one hero
        heroes = [i for i, c in enumerate(cards) if c.get('is_hero')]
        if not heroes and cards:
            cards[0]['is_hero'] = True
        elif len(heroes) > 1:
            for i in heroes[1:]:
                cards[i].pop('is_hero', None)
        info['cards'] = cards
        data['infographic'] = info

        # closing — must be dict, not string
        closing = data.get('closing')
        if not isinstance(closing, dict):
            closing = {}
        data['closing'] = closing

        # intro — normalize: if string, wrap in {"paragraph": "..."}
        intro = data.get('intro')
        if isinstance(intro, str):
            intro = {'paragraph': intro}
        elif not isinstance(intro, dict):
            intro = {}
        data['intro'] = intro

        # pro_tips — normalize: if list, wrap in {"items": list}
        pro_tips = data.get('pro_tips')
        if isinstance(pro_tips, list):
            pro_tips = {'items': [{'heading': '', 'bullets': [b]} if isinstance(b, str) else b for b in pro_tips]}
        elif not isinstance(pro_tips, dict):
            pro_tips = {}
        data['pro_tips'] = pro_tips

        # money_map — normalize: if list, wrap in {"rows": list}
        money_map = data.get('money_map')
        if isinstance(money_map, list):
            money_map = {'rows': money_map}
        elif not isinstance(money_map, dict):
            money_map = {}
        data['money_map'] = money_map

        # timestamp_index — normalize: if list, wrap in {"rows": list}
        ts_index = data.get('timestamp_index')
        if isinstance(ts_index, list):
            ts_index = {'rows': ts_index}
        elif not isinstance(ts_index, dict):
            ts_index = {}
        data['timestamp_index'] = ts_index

        # Generic string cap: truncate any string > 1000 chars
        def _cap(o):
            if isinstance(o, dict):
                return {k: _cap(v) for k, v in o.items()}
            if isinstance(o, list):
                return [_cap(v) for v in o]
            if isinstance(o, str) and len(o) > 1000:
                return o[:997] + '...'
            return o
        data = _cap(data)

        # Build dynamic layout: only include sections that have real content
        data['layout'] = LLMClient._build_layout(data)
        return data

    @staticmethod
    def _build_layout(data: dict) -> list[dict]:
        """Convert flat summary dict into an ordered layout array.

        Each entry in the returned list has:
            type       – one of cover / intro / meta / chapter / pro_tips /
                         money_map / quotes / infographic / timestamp_index / closing
            data       – the content dict for that section
            eyebrow    – gold prefix shown in the title line (number or label)
            en_eyebrow – English subtitle rendered above the title

        Sections with no meaningful content are OMITTED entirely, so the
        renderer never shows empty / placeholder sections.
        """
        layout: list[dict] = []

        # 1. Cover (if display_title exists)
        cover = data.get('cover')
        if isinstance(cover, dict) and cover.get('display_title'):
            layout.append({'type': 'cover', 'data': cover})

        # 2. Meta table – always present; intro paragraph inlined here
        meta = data.get('meta') or {}
        intro = data.get('intro')
        if isinstance(intro, dict) and intro.get('paragraph'):
            meta = dict(meta)
            meta['_intro'] = intro['paragraph']
        layout.append({
            'type': 'meta', 'data': meta,
            'eyebrow': '01', 'en_eyebrow': 'At a Glance',
        })

        # 3. Infographic – visual summary right after meta, before chapters
        info = data.get('infographic')
        if isinstance(info, dict):
            cards = info.get('cards') or []
            if cards:
                layout.append({
                    'type': 'infographic', 'data': info,
                    'eyebrow': 'INFO', 'en_eyebrow': 'Infographic',
                })

        # 4. Chapters (main content sections)
        sections = data.get('sections') or []
        chapter_num = 2
        for sec in sections:
            if isinstance(sec, dict) and (sec.get('title') or sec.get('body')):
                sec_title = sec.get('title') or sec.get('body', '')[:30] + '…'
                sec.setdefault('title', sec_title)
                layout.append({
                    'type': 'chapter', 'data': sec,
                    'eyebrow': f'{chapter_num:02d}',
                    'en_eyebrow': sec.get('eyebrow') or '',
                })
                chapter_num += 1

        # 5. Pro tips – only if items exist
        pro_tips = data.get('pro_tips')
        if isinstance(pro_tips, dict):
            items = pro_tips.get('items') or []
            if items and any(isinstance(i, dict) for i in items):
                layout.append({
                    'type': 'pro_tips', 'data': pro_tips,
                    'eyebrow': 'TIPS', 'en_eyebrow': 'Pro Tips',
                })

        # 6. Money map – only if ≥ 3 meaningful rows
        money_map = data.get('money_map')
        if isinstance(money_map, dict):
            rows = money_map.get('rows') or []
            if len(rows) >= 3:
                layout.append({
                    'type': 'money_map', 'data': money_map,
                    'eyebrow': 'MONEY', 'en_eyebrow': 'Money Map',
                })

        # 7. Quotes – only if ≥ 3 non-empty
        quotes = data.get('quotes')
        if quotes and isinstance(quotes, list):
            qs = [q for q in quotes if q]
            if len(qs) >= 3:
                layout.append({
                    'type': 'quotes', 'data': {'items': qs},
                    'eyebrow': 'QUOTES', 'en_eyebrow': 'Key Quotes',
                })

        # 8. Timestamp index – only if ≥ 3 rows; normalize field names
        ts = data.get('timestamp_index')
        if isinstance(ts, dict):
            rows = ts.get('rows') or []
            if rows:
                for r in rows:
                    if 'time' in r and 'range' not in r:
                        r['range'] = r.pop('time')
                    if 'title' in r and 'topic' not in r:
                        r['topic'] = r.pop('title')
                    # timestamp_sec (integer seconds) → "MM:SS"
                    ts_sec = r.get('timestamp_sec') or r.get('timestamp') or None
                    if ts_sec and not r.get('range'):
                        try:
                            sec = int(ts_sec)
                            mm, ss = divmod(sec, 60)
                            h, mm = divmod(mm, 60)
                            if h:
                                r['range'] = f'{h:02d}:{mm:02d}:{ss:02d}'
                            else:
                                r['range'] = f'{mm:02d}:{ss:02d}'
                        except (TypeError, ValueError):
                            pass
                    # start/end pair → "start-end" range
                    if r.get('start') is not None and r.get('end') is not None and not r.get('range'):
                        r['range'] = f'{r["start"]}-{r["end"]}'
                    # time_range string alias
                    tr = r.get('time_range') or ''
                    if tr and not r.get('range'):
                        r['range'] = str(tr)
                    # description / content → topic fallback
                    if not r.get('topic'):
                        r['topic'] = r.get('description') or r.get('content') or ''
                if len(rows) >= 3:
                    layout.append({
                        'type': 'timestamp_index', 'data': ts,
                        'eyebrow': 'TIME', 'en_eyebrow': 'Timestamp',
                    })

        # 9. Closing – only if disclaimer or credit
        closing = data.get('closing')
        if isinstance(closing, dict) and (closing.get('disclaimer') or closing.get('credit')):
            layout.append({'type': 'closing', 'data': closing})

        return layout