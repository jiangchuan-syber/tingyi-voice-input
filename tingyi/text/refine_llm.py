# -*- coding: utf-8 -*-
"""可选 DeepSeek LLM 润色（与工作经历挖掘项目共用 DEEPSEEK_* 环境变量）。"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_REFINE_SYSTEM = """你是语音转文字的后处理助手。用户输入来自语音识别，可能有口语、重复或标点问题。
请只做最小必要修改：去口头语、补标点、保持原意，不要编造事实，不要扩写。
只输出润色后的正文，不要解释。"""


def llm_refine_available() -> bool:
    key = (os.getenv("TINGYI_REFINE_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or "").strip()
    enabled = os.getenv("TINGYI_REFINE_ENABLED", "auto").lower()
    if enabled in ("0", "false", "no", "off"):
        return False
    if enabled in ("1", "true", "yes", "on"):
        return bool(key)
    return bool(key)


def llm_refine(text: str) -> str:
    if not text.strip():
        return text

    api_key = (os.getenv("TINGYI_REFINE_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or "").strip()
    if not api_key:
        return text

    base_url = (
        os.getenv("TINGYI_REFINE_BASE_URL")
        or os.getenv("DEEPSEEK_API_BASE")
        or "https://api.deepseek.com"
    ).rstrip("/")
    model = (
        os.getenv("TINGYI_REFINE_MODEL")
        or os.getenv("DEEPSEEK_MODEL")
        or "deepseek-chat"
    ).strip()

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _REFINE_SYSTEM},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        out = (resp.choices[0].message.content or "").strip()
        return out or text
    except Exception:
        logger.exception("LLM refine failed")
        return text
