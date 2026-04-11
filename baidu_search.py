"""百度千帆 AI搜索 API 封装

支持两种接口：
1. web_search  — 纯检索，返回搜索结果列表（title / url / snippet）
2. chat/completions — AI 搜索（大模型 + 检索），返回总结 + 参考链接

本模块只用 web_search（纯检索），保证返回结构与原 google_cse_search 一致。

鉴权方式：
  使用百度智能云千帆平台的 API Key（格式 bce-v3/ALTAK-...），
  直接作为 Bearer Token 放入 Authorization Header，无需 access_token。
"""

import asyncio
import json
import logging
import os
from typing import Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
BAIDU_SEARCH_API_KEY = os.getenv("BAIDU_SEARCH_API_KEY", "").strip()

# 百度千帆 AI 搜索 — 纯检索 endpoint
BAIDU_WEB_SEARCH_URL = "https://qianfan.baidubce.com/v2/ai_search/web_search"

# AI 搜索（大模型总结 + 检索）endpoint，备用
BAIDU_AI_SEARCH_CHAT_URL = "https://qianfan.baidubce.com/v2/ai_search/chat/completions"


# ---------------------------------------------------------------------------
# 核心实现
# ---------------------------------------------------------------------------

async def baidu_web_search(
    query: str,
    max_results: int = 5,
    api_key: str | None = None,
) -> list[dict[str, str]]:
    """
    调用百度千帆 AI搜索 web_search 接口，返回标准搜索结果列表。

    返回格式（与原 google_cse_search 保持一致）：
    [
        {
            "title": "网页标题",
            "url": "https://...",
            "snippet": "摘要",
            "source": "Baidu"
        },
        ...
    ]
    """
    key = (api_key or BAIDU_SEARCH_API_KEY or os.getenv("BAIDU_SEARCH_API_KEY", "")).strip()
    if not key:
        logger.warning("BAIDU_SEARCH_API_KEY 未配置，跳过搜索。")
        return []

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }

    payload = {
        "query": query,
        "top_k": max(1, min(max_results, 10)),
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(BAIDU_WEB_SEARCH_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        # 如果 web_search endpoint 返回 404/403，尝试 fallback 到 chat/completions
        logger.warning("百度 web_search 接口返回 %s，尝试 AI 搜索 fallback...", exc.response.status_code)
        return await _baidu_ai_search_fallback(query, max_results, key)
    except Exception as exc:
        logger.error("百度搜索请求失败: %s", exc)
        return []

    return _parse_web_search_response(data)


async def _baidu_ai_search_fallback(
    query: str,
    max_results: int,
    api_key: str,
) -> list[dict[str, str]]:
    """
    Fallback: 使用 AI 搜索 chat/completions 接口。
    该接口会返回大模型总结 + references 列表。
    我们只提取 references 作为搜索结果。
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "messages": [
            {"role": "user", "content": query}
        ],
        "stream": False,
        "enable_deep_search": False,
        "resource_type_filter": [{"type": "web", "top_k": max(1, min(max_results, 10))}],
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(BAIDU_AI_SEARCH_CHAT_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error("百度 AI 搜索 fallback 也失败: %s", exc)
        return []

    return _parse_ai_search_response(data)


def _parse_web_search_response(data: dict) -> list[dict[str, str]]:
    """解析 /v2/ai_search/web_search 的响应"""
    results: list[dict[str, str]] = []

    # 尝试多种可能的响应结构
    search_results = (
        data.get("search_results")
        or data.get("results")
        or data.get("data", {}).get("search_results")
        or data.get("data", {}).get("results")
        or []
    )

    for item in search_results:
        url = (item.get("url") or item.get("link") or "").strip()
        if not url:
            continue
        results.append({
            "title": (item.get("title") or "参考链接").strip(),
            "url": url,
            "snippet": (item.get("content") or item.get("snippet") or item.get("abstract") or "").strip(),
            "source": (item.get("source_name") or "Baidu").strip(),
        })

    return results


def _parse_ai_search_response(data: dict) -> list[dict[str, str]]:
    """解析 /v2/ai_search/chat/completions 的响应（提取 references）"""
    results: list[dict[str, str]] = []

    references = (
        data.get("references")
        or data.get("search_results")
        or []
    )

    for item in references:
        url = (item.get("url") or item.get("link") or "").strip()
        if not url:
            continue
        results.append({
            "title": (item.get("title") or "参考链接").strip(),
            "url": url,
            "snippet": (item.get("content") or item.get("snippet") or "").strip(),
            "source": (item.get("source_name") or "Baidu").strip(),
        })

    return results


# ---------------------------------------------------------------------------
# 便捷同步包装（供 LangChain @tool 使用）
# ---------------------------------------------------------------------------

def baidu_web_search_sync(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """同步版本的百度搜索，内部调用异步实现。"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # 在已有事件循环中（如 FastAPI），使用线程
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, baidu_web_search(query, max_results))
            return future.result(timeout=20)
    else:
        return asyncio.run(baidu_web_search(query, max_results))
