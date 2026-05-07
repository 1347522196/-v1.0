from __future__ import annotations

from statistics import mean
from typing import Any

import requests

from ..config import settings
from .ai_settings import DEFAULT_MODEL, load_ai_settings
from .intel_repository import list_keywords
from .product_repository import list_products


DEEPSEEK_BASE_URL = "https://api.deepseek.com/chat/completions"
ALLOWED_MODELS = {"deepseek-v4-flash", "deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner"}


def _currency_bucket(items: list[dict[str, Any]]) -> str:
    currencies = sorted({str(item.get("currency") or "USD") for item in items})
    return ", ".join(currencies) if currencies else "USD"


def _safe_mean(values: list[float]) -> float:
    clean_values = [float(value) for value in values]
    if not clean_values:
        return 0
    return round(mean(clean_values), 2)


def _product_dataset(*, only_favorites: bool) -> dict[str, Any]:
    items, total = list_products(
        only_favorites=only_favorites,
        sort_by="comprehensive",
        sort_order="desc",
        page=1,
        page_size=30,
    )
    avg_price = _safe_mean([item["price"] for item in items if item.get("price") is not None])
    avg_rating = _safe_mean([item["rating"] for item in items if item.get("rating") is not None])
    avg_reviews = _safe_mean([item["review_count"] for item in items if item.get("review_count") is not None])
    top_items = []
    for item in items[:15]:
        top_items.append(
            {
                "title": item.get("title"),
                "asin": item.get("asin"),
                "marketplace": item.get("marketplace"),
                "keyword": item.get("keyword"),
                "price": item.get("price"),
                "currency": item.get("currency"),
                "rating": item.get("rating"),
                "review_count": item.get("review_count"),
                "estimated_monthly_bought": item.get("estimated_monthly_bought"),
                "opportunity_score": item.get("opportunity_score"),
                "is_prime": bool(item.get("is_prime")),
                "status": item.get("custom_status"),
                "note": item.get("note"),
            }
        )
    return {
        "scope": "favorites" if only_favorites else "products",
        "total_items": total,
        "sample_size": len(items),
        "currencies": _currency_bucket(items),
        "avg_price": avg_price,
        "avg_rating": avg_rating,
        "avg_review_count": avg_reviews,
        "top_items": top_items,
    }


def _keyword_dataset() -> dict[str, Any]:
    keywords = list_keywords()
    top_keywords = []
    for item in keywords[:20]:
        top_keywords.append(
            {
                "keyword": item.get("keyword"),
                "marketplace": item.get("marketplace"),
                "department": item.get("department"),
                "priority": item.get("priority"),
                "status": item.get("status"),
                "last_result_count": item.get("last_result_count"),
                "last_scraped_at": item.get("last_scraped_at"),
                "note": item.get("note"),
            }
        )
    return {
        "scope": "keywords",
        "total_items": len(keywords),
        "top_keywords": top_keywords,
    }


def build_analysis_dataset(scope: str) -> dict[str, Any]:
    if scope == "favorites":
        return _product_dataset(only_favorites=True)
    if scope == "keywords":
        return _keyword_dataset()
    return _product_dataset(only_favorites=False)


def analyze_with_deepseek(*, scope: str, user_question: str = "") -> dict[str, Any]:
    ai_settings = load_ai_settings()
    api_key = str(ai_settings.get("api_key") or "").strip()
    if not api_key:
        raise RuntimeError("尚未填写 DeepSeek API Key，请先在 AI 分析面板输入本次会话使用的 Key。")

    model = str(ai_settings.get("model") or DEFAULT_MODEL).strip()
    if model not in ALLOWED_MODELS:
        model = DEFAULT_MODEL

    dataset = build_analysis_dataset(scope)
    scope_label = {
        "products": "商品库",
        "favorites": "收藏夹",
        "keywords": "关键词库",
    }.get(scope, "商品库")

    system_prompt = (
        "你是一名亚马逊运营分析助手。"
        "请基于给定的数据，用简体中文输出结构清晰、可执行的分析结果。"
        "重点包括：整体判断、值得优先关注的对象、风险点、下一步建议。"
        "如果数据有限，要明确说明哪些结论是基于当前样本。"
        "输出请使用 markdown，控制在 4 到 8 个要点内，尽量务实。"
    )

    user_prompt = (
        f"请分析当前{scope_label}数据。\n\n"
        f"用户补充问题：{user_question.strip() or '请给我最值得执行的运营建议。'}\n\n"
        f"数据样本：{dataset}"
    )

    response = requests.post(
        DEEPSEEK_BASE_URL,
        timeout=max(30, settings.request_timeout_seconds * 2),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "thinking": {"type": "disabled"},
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 1800,
        },
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        try:
            payload = response.json()
        except ValueError:
            raise
        error_payload = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error_payload, dict):
            message = error_payload.get("message") or error_payload.get("type") or str(error_payload)
            raise RuntimeError(f"DeepSeek 返回错误：{message}") from exc
        raise
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    usage = payload.get("usage", {})
    return {
        "scope": scope,
        "model": model,
        "analysis": content,
        "dataset_summary": {
            "total_items": dataset.get("total_items", 0),
            "sample_size": dataset.get("sample_size", dataset.get("total_items", 0)),
        },
        "usage": usage,
    }
