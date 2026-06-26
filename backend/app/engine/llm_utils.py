"""Shared utility functions for LLM/VLM operators.

Extracted from text_llm_operator.py and sniffer_operator.py to avoid duplication.
"""

import json
import logging
import re

from app.services.ai_config_service import get_ai_config

logger = logging.getLogger(__name__)


async def _get_ai_config(model_type: str = "text", requested_model: str = None) -> dict:
    """Thin async wrapper around ai_config_service.get_ai_config."""
    return await get_ai_config(model_type=model_type, requested_model=requested_model)


def _safe_json_parse(text: str) -> dict:
    """Robust JSON extraction from LLM/VLM responses.

    Handles markdown fences, nested braces, trailing commas, etc.
    Raises ValueError if all strategies fail.
    """
    if not text or not text.strip():
        raise ValueError("Empty or whitespace-only response")

    text = text.strip()

    # Strategy 1: Direct parse (fast path)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Remove markdown code fences
    fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find first JSON object with balanced braces (handles one level of nesting)
    brace_match = re.search(r'\{(?:[^{}]|\{[^{}]*\})*\}', text)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass

    # Strategy 4: Clean trailing commas / single quotes and retry
    cleaned = re.sub(r',(\s*[}\]])', r'\1', text)       # trailing commas before } or ]
    cleaned = re.sub(r"'", '"', cleaned)                  # single quotes → double quotes
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    brace_match = re.search(r'\{(?:[^{}]|\{[^{}]*\})*\}', cleaned)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Cannot parse JSON from response (first 300 chars): {text[:300]}")
