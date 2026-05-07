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


def _estimate_opportunity_score(product: dict[str, Any]) -> int:
    rating = float(product.get("rating") or 0)
    reviews = int(product.get("review_count") or 0)
    price = float(product.get("price") or 0)
    score = 55
    score += 12 if price >= 20 else 4
    score += 10 if reviews < 200 else 0
    score += 6 if rating >= 4.2 else 0
    score += 5 if not product.get("is_sponsored") else -4
    return max(1, min(100, floor(score)))


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
                "opportunity_score": raw_product.get("opportunity_score")
                or _estimate_opportunity_score(raw_product),
            }
            connection.execute(
                """
                INSERT INTO products (
                    asin, marketplace, keyword, title, product_url, image_url,
                    price, currency, rating, review_count, badge, is_prime,
                    is_sponsored, availability, scraped_at, created_at, updated_at,
                    brand, category_path, source_rank, opportunity_score
                ) VALUES (
                    :asin, :marketplace, :keyword, :title, :product_url, :image_url,
                    :price, :currency, :rating, :review_count, :badge, :is_prime,
                    :is_sponsored, :availability, :scraped_at, :created_at, :updated_at,
                    :brand, :category_path, :source_rank, :opportunity_score
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
                MIN(COALESCE(review_count, 0), 5000) * 0.01 +
                CASE WHEN is_prime = 1 THEN 6 ELSE 0 END +
                CASE WHEN is_sponsored = 1 THEN -4 ELSE 2 END +
                CASE WHEN is_favorite = 1 THEN 8 ELSE 0 END
            )
        """,
        "opportunity_score": "COALESCE(opportunity_score, 0)",
        "estimated_sales": "COALESCE(review_count, 0)",
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
    data["product_url"] = resolve_product_url(
        asin=str(data.get("asin") or ""),
        marketplace=str(data.get("marketplace") or "com"),
        title=str(data.get("title") or ""),
        keyword=str(data.get("keyword") or ""),
        product_url=str(data.get("product_url") or ""),
    )
    return data
