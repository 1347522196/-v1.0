from __future__ import annotations

from datetime import datetime, timezone
from math import floor
from typing import Any
from urllib.parse import quote_plus

from ..database import get_connection
from .amazon_scraper import DEMO_PRODUCTS


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _infer_brand(title: str) -> str:
    words = [part for part in title.split() if part.strip()]
    return words[0][:40] if words else ""


OPPORTUNITY_WEIGHTS: list[tuple[str, str, int]] = [
    ("demand_signal", "需求热度", 18),
    ("competition_signal", "竞争强度", 22),
    ("rating_quality", "评分质量", 18),
    ("price_band", "价格带", 12),
    ("visibility", "搜索位次", 14),
    ("prime_advantage", "Prime 优势", 8),
    ("ad_pressure", "广告压力", 8),
]


def _clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))


def _score_demand(product: dict[str, Any]) -> tuple[float, str]:
    monthly_bought = product.get("estimated_monthly_bought")
    reviews = product.get("review_count")
    if monthly_bought is not None:
        bought = int(monthly_bought)
        if bought >= 5000:
            return 100, f"月购买量估算约 {bought}+，需求非常强"
        if bought >= 2000:
            return 90, f"月购买量估算约 {bought}+，需求很强"
        if bought >= 1000:
            return 80, f"月购买量估算约 {bought}+，需求较强"
        if bought >= 300:
            return 66, f"月购买量估算约 {bought}+，需求中等"
        if bought >= 100:
            return 52, f"月购买量估算约 {bought}+，需求偏弱但仍有动销"
        return 36, f"月购买量估算约 {bought}+，需求偏弱"
    if reviews is None:
        return 32, "缺少月购买量和评论沉淀数据，需求热度可信度一般"
    review_count = int(reviews)
    if review_count >= 5000:
        return 72, f"评论数 {review_count}，需求强但竞争也较重"
    if review_count >= 1000:
        return 58, f"评论数 {review_count}，需求不错"
    if review_count >= 200:
        return 45, f"评论数 {review_count}，需求中等"
    return 30, f"评论数 {review_count}，需求数据偏少"


def _score_competition(product: dict[str, Any]) -> tuple[float, str]:
    reviews = product.get("review_count")
    if reviews is None:
        return 35, "评论数缺失，竞争强度只能保守估计"
    review_count = int(reviews)
    if review_count == 0:
        return 55, "评论数为 0，可能是新链接，也可能是页面未完整展示"
    if review_count <= 50:
        return 84, f"评论数 {review_count}，竞争较轻"
    if review_count <= 200:
        return 96, f"评论数 {review_count}，竞争轻且更适合切入"
    if review_count <= 500:
        return 88, f"评论数 {review_count}，仍有较好切入空间"
    if review_count <= 1500:
        return 72, f"评论数 {review_count}，竞争开始加重"
    if review_count <= 5000:
        return 48, f"评论数 {review_count}，竞争明显偏重"
    return 26, f"评论数 {review_count}，竞争很重"


def _score_rating(product: dict[str, Any]) -> tuple[float, str]:
    rating = product.get("rating")
    if rating is None:
        return 40, "缺少评分数据"
    score = float(rating)
    if score >= 4.7:
        return 96, f"评分 {score}，口碑非常强"
    if score >= 4.5:
        return 88, f"评分 {score}，口碑优秀"
    if score >= 4.2:
        return 76, f"评分 {score}，口碑良好"
    if score >= 4.0:
        return 58, f"评分 {score}，口碑一般"
    return 26, f"评分 {score}，口碑偏弱"


def _score_price(product: dict[str, Any]) -> tuple[float, str]:
    price = product.get("price")
    if price is None:
        return 40, "缺少价格数据"
    value = float(price)
    if 20 <= value <= 120:
        return 92, f"价格 {value:.2f}，处在较友好的主流价格带"
    if 12 <= value < 20:
        return 68, f"价格 {value:.2f}，偏低价，需要靠效率取胜"
    if 120 < value <= 220:
        return 74, f"价格 {value:.2f}，客单价不错，但转化门槛更高"
    if value < 12:
        return 36, f"价格 {value:.2f}，价格带偏低"
    return 58, f"价格 {value:.2f}，属于高价带"


def _score_visibility(product: dict[str, Any]) -> tuple[float, str]:
    source_rank = product.get("source_rank")
    if source_rank is None:
        return 40, "缺少搜索位次数据"
    rank = int(source_rank)
    if rank <= 8:
        return 96, f"搜索位次第 {rank} 位，曝光很强"
    if rank <= 24:
        return 84, f"搜索位次第 {rank} 位，曝光较强"
    if rank <= 48:
        return 70, f"搜索位次第 {rank} 位，曝光中等"
    if rank <= 96:
        return 54, f"搜索位次第 {rank} 位，曝光偏后"
    return 34, f"搜索位次第 {rank} 位，曝光较弱"


def _score_prime(product: dict[str, Any]) -> tuple[float, str]:
    is_prime = bool(product.get("is_prime"))
    return (100, "带 Prime 标记，履约体验更友好") if is_prime else (45, "无 Prime 标记")


def _score_sponsored(product: dict[str, Any]) -> tuple[float, str]:
    is_sponsored = bool(product.get("is_sponsored"))
    return (35, "Sponsored 广告位，排名可能更依赖投放") if is_sponsored else (88, "非 Sponsored，自然位表现更有参考价值")


def _calculate_opportunity_model(product: dict[str, Any]) -> dict[str, Any]:
    component_scores = {
        "demand_signal": _score_demand(product),
        "competition_signal": _score_competition(product),
        "rating_quality": _score_rating(product),
        "price_band": _score_price(product),
        "visibility": _score_visibility(product),
        "prime_advantage": _score_prime(product),
        "ad_pressure": _score_sponsored(product),
    }

    breakdown: list[dict[str, Any]] = []
    total_score = 0.0
    for key, label, weight in OPPORTUNITY_WEIGHTS:
        component_score, reason = component_scores[key]
        contribution = round(_clamp(component_score) * weight / 100, 1)
        total_score += contribution
        breakdown.append(
            {
                "key": key,
                "label": label,
                "weight": weight,
                "component_score": round(_clamp(component_score), 1),
                "contribution": contribution,
                "reason": reason,
            }
        )

    return {
        "score": max(1, min(100, floor(total_score))),
        "breakdown": breakdown,
    }


def resolve_product_url(
    *,
    asin: str,
    marketplace: str,
    title: str = "",
    keyword: str = "",
    product_url: str = "",
) -> str:
    asin_value = (asin or "").strip().upper()
    marketplace_value = (marketplace or "com").strip()

    if _looks_like_real_asin(asin_value):
        return f"https://www.amazon.{marketplace_value}/dp/{asin_value}"

    query = (title or keyword or asin_value or "hardware tools").strip()
    return f"https://www.amazon.{marketplace_value}/s?k={quote_plus(query)}"


def _looks_like_real_asin(value: str) -> bool:
    if not value or len(value) != 10:
        return False
    if not value.isalnum():
        return False
    if value.startswith("B0DEMO"):
        return False
    return True


def upsert_products(products: list[dict[str, Any]]) -> int:
    inserted_or_updated = 0
    now = _utc_now()

    with get_connection() as connection:
        for index, raw_product in enumerate(products, start=1):
            product = {
                **raw_product,
                "opportunity_score": _calculate_opportunity_model(raw_product)["score"],
                "brand": raw_product.get("brand") or _infer_brand(raw_product.get("title", "")),
                "category_path": raw_product.get("category_path") or "Hardware > Tools",
                "source_rank": raw_product.get("source_rank") or index,
                "product_url": resolve_product_url(
                    asin=str(raw_product.get("asin") or ""),
                    marketplace=str(raw_product.get("marketplace") or "com"),
                    title=str(raw_product.get("title") or ""),
                    keyword=str(raw_product.get("keyword") or ""),
                    product_url=str(raw_product.get("product_url") or ""),
                ),
                "estimated_monthly_bought": raw_product.get("estimated_monthly_bought"),
            }
            connection.execute(
                """
                INSERT INTO products (
                    asin, marketplace, keyword, title, product_url, image_url,
                    price, currency, rating, review_count, badge, is_prime,
                    is_sponsored, availability, scraped_at, created_at, updated_at,
                    brand, category_path, source_rank, estimated_monthly_bought, opportunity_score
                ) VALUES (
                    :asin, :marketplace, :keyword, :title, :product_url, :image_url,
                    :price, :currency, :rating, :review_count, :badge, :is_prime,
                    :is_sponsored, :availability, :scraped_at, :created_at, :updated_at,
                    :brand, :category_path, :source_rank, :estimated_monthly_bought, :opportunity_score
                )
                ON CONFLICT(asin, marketplace) DO UPDATE SET
                    keyword = excluded.keyword,
                    title = excluded.title,
                    product_url = excluded.product_url,
                    image_url = excluded.image_url,
                    price = excluded.price,
                    currency = excluded.currency,
                    rating = excluded.rating,
                    review_count = excluded.review_count,
                    badge = excluded.badge,
                    is_prime = excluded.is_prime,
                    is_sponsored = excluded.is_sponsored,
                    availability = excluded.availability,
                    scraped_at = excluded.scraped_at,
                    updated_at = excluded.updated_at,
                    brand = excluded.brand,
                    category_path = excluded.category_path,
                    source_rank = excluded.source_rank,
                    estimated_monthly_bought = excluded.estimated_monthly_bought,
                    opportunity_score = excluded.opportunity_score
                """,
                {
                    **product,
                    "is_prime": int(bool(product.get("is_prime"))),
                    "is_sponsored": int(bool(product.get("is_sponsored"))),
                    "created_at": now,
                    "updated_at": now,
                },
            )
            inserted_or_updated += 1

    return inserted_or_updated


def seed_demo_products() -> int:
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM products
            WHERE asin = 'B0DEMO003' AND marketplace = 'co.uk'
            """
        )
    return upsert_products([product.to_record() for product in DEMO_PRODUCTS])


def list_products(
    *,
    query: str = "",
    marketplace: str = "",
    status: str = "",
    only_favorites: bool = False,
    min_price: float | None = None,
    max_price: float | None = None,
    keyword: str = "",
    sort_by: str = "comprehensive",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    filters: list[str] = []
    params: dict[str, Any] = {}

    if query:
        filters.append(
            "(title LIKE :query OR asin LIKE :query OR note LIKE :query OR brand LIKE :query)"
        )
        params["query"] = f"%{query}%"
    if marketplace:
        filters.append("marketplace = :marketplace")
        params["marketplace"] = marketplace
    if status:
        filters.append("custom_status = :status")
        params["status"] = status
    if keyword:
        filters.append("keyword = :keyword")
        params["keyword"] = keyword
    if only_favorites:
        filters.append("is_favorite = 1")
    if min_price is not None:
        filters.append("price >= :min_price")
        params["min_price"] = min_price
    if max_price is not None:
        filters.append("price <= :max_price")
        params["max_price"] = max_price

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    offset = (page - 1) * page_size
    order_clause = _build_order_clause(sort_by=sort_by, sort_order=sort_order)

    with get_connection() as connection:
        total = connection.execute(
            f"SELECT COUNT(*) FROM products {where_clause}",
            params,
        ).fetchone()[0]

        rows = connection.execute(
            f"""
            SELECT *
            FROM products
            {where_clause}
            ORDER BY {order_clause}
            LIMIT :limit OFFSET :offset
            """,
            {**params, "limit": page_size, "offset": offset},
        ).fetchall()

    return [_row_to_dict(row) for row in rows], total


def _build_order_clause(*, sort_by: str, sort_order: str) -> str:
    direction = "ASC" if str(sort_order).lower() == "asc" else "DESC"
    expressions = {
        "comprehensive": """
            (
                COALESCE(opportunity_score, 0) * 1.8 +
                COALESCE(rating, 0) * 12 +
                MIN(COALESCE(estimated_monthly_bought, COALESCE(review_count, 0)), 5000) * 0.01 +
                CASE WHEN is_prime = 1 THEN 6 ELSE 0 END +
                CASE WHEN is_sponsored = 1 THEN -4 ELSE 2 END +
                CASE WHEN is_favorite = 1 THEN 8 ELSE 0 END
            )
        """,
        "opportunity_score": "COALESCE(opportunity_score, 0)",
        "estimated_sales": "COALESCE(estimated_monthly_bought, COALESCE(review_count, 0))",
        "review_count": "COALESCE(review_count, 0)",
        "rating": "COALESCE(rating, 0)",
        "price": "COALESCE(price, 0)",
        "source_rank": "CASE WHEN source_rank IS NULL THEN 999999 ELSE source_rank END",
        "newest": "scraped_at",
        "updated": "updated_at",
        "favorite": "COALESCE(is_favorite, 0)",
        "prime": "COALESCE(is_prime, 0)",
    }
    expression = expressions.get(sort_by, expressions["comprehensive"])
    return f"{expression} {direction}, scraped_at DESC, updated_at DESC, id DESC"


def get_product(product_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()

    return _row_to_dict(row) if row else None


def get_product_by_asin(asin: str, marketplace: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM products
            WHERE asin = ? AND marketplace = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (asin, marketplace),
        ).fetchone()

    return _row_to_dict(row) if row else None


def update_product(product_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    assignments: list[str] = []
    params: dict[str, Any] = {"id": product_id, "updated_at": _utc_now()}

    if "custom_status" in payload and payload["custom_status"] is not None:
        assignments.append("custom_status = :custom_status")
        params["custom_status"] = payload["custom_status"]
    if "note" in payload and payload["note"] is not None:
        assignments.append("note = :note")
        params["note"] = payload["note"].strip()
    if "is_favorite" in payload and payload["is_favorite"] is not None:
        assignments.append("is_favorite = :is_favorite")
        params["is_favorite"] = int(bool(payload["is_favorite"]))

    if not assignments:
        return get_product(product_id)

    assignments.append("updated_at = :updated_at")

    with get_connection() as connection:
        connection.execute(
            f"UPDATE products SET {', '.join(assignments)} WHERE id = :id",
            params,
        )

    return get_product(product_id)


def toggle_favorite(product_id: int) -> dict[str, Any] | None:
    current = get_product(product_id)
    if not current:
        return None
    return update_product(product_id, {"is_favorite": not bool(current["is_favorite"])})


def delete_product(product_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
        return cursor.rowcount > 0


def clear_products() -> int:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM products")
    return cursor.rowcount


def _row_to_dict(row) -> dict[str, Any]:
    data = dict(row)
    data["is_prime"] = bool(data["is_prime"])
    data["is_sponsored"] = bool(data["is_sponsored"])
    data["is_favorite"] = bool(data["is_favorite"])
    opportunity_model = _calculate_opportunity_model(data)
    data["opportunity_score"] = opportunity_model["score"]
    data["opportunity_breakdown"] = opportunity_model["breakdown"]
    data["product_url"] = resolve_product_url(
        asin=str(data.get("asin") or ""),
        marketplace=str(data.get("marketplace") or "com"),
        title=str(data.get("title") or ""),
        keyword=str(data.get("keyword") or ""),
        product_url=str(data.get("product_url") or ""),
    )
    return data
