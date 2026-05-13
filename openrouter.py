import aiohttp
import asyncio
import logging
import time
from typing import Optional
from config import (
    OPENROUTER_BASE_URL,
    OPENROUTER_API_KEY,
    REQUEST_TIMEOUT,
    MAX_TOKENS,
    MAX_RETRIES,
    ULTIMATE_FALLBACK_TEXT,
)

logger = logging.getLogger(__name__)

_RETRY_DELAYS = [1.0, 2.0]
_RETRY_ON_STATUS = {429, 500, 502, 503, 504}


async def call_openrouter(
    messages: list,
    model: str,
    max_tokens: int = MAX_TOKENS,
    temperature: float = 0.7,
) -> Optional[str]:
    """Single attempt to call a model. Returns text or None on any failure."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://netonai.bot",
        "X-Title": "NetonAI",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    logger.info(f"Model {model} responded successfully")
                    return content.strip()
                else:
                    text = await resp.text()
                    logger.warning(
                        f"Model {model} returned {resp.status}: {text[:200]}"
                    )
                    return None
    except asyncio.TimeoutError:
        logger.warning(f"Model {model} timed out after {REQUEST_TIMEOUT}s")
        return None
    except Exception as e:
        logger.error(f"Model {model} error: {e}")
        return None


async def call_openrouter_with_retry(
    messages: list,
    model: str,
    max_tokens: int = MAX_TOKENS,
    temperature: float = 0.7,
) -> Optional[str]:
    """
    Call a single model with up to MAX_RETRIES attempts.
    Applies exponential-style delays between retries.
    Returns text on first success, None if all attempts fail.
    """
    for attempt in range(MAX_RETRIES):
        result = await call_openrouter(messages, model, max_tokens, temperature)
        if result:
            return result
        if attempt < MAX_RETRIES - 1:
            delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
            logger.info(f"Retry {attempt + 1}/{MAX_RETRIES - 1} for {model} in {delay}s")
            await asyncio.sleep(delay)
    return None


async def call_with_fallback(
    messages: list,
    models: list,
    max_tokens: int = MAX_TOKENS,
    temperature: float = 0.7,
) -> tuple[str, Optional[str]]:
    """
    Try each model in order with retries. Never returns (None, None).
    On total failure returns (ULTIMATE_FALLBACK_TEXT, 'fallback').
    """
    start = time.time()
    for model in models:
        logger.info(f"Trying model: {model}")
        result = await call_openrouter_with_retry(
            messages, model, max_tokens, temperature
        )
        if result:
            elapsed = round(time.time() - start, 2)
            logger.info(f"Got response from {model} in {elapsed}s")
            return result, model

    logger.error(f"All models and retries exhausted: {models}")
    return ULTIMATE_FALLBACK_TEXT, "fallback"


async def get_available_models() -> list:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    }
    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                f"{OPENROUTER_BASE_URL}/models", headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    free_models = [
                        m["id"]
                        for m in data.get("data", [])
                        if ":free" in m.get("id", "")
                    ]
                    return free_models
    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
    return []
