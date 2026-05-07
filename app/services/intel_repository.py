from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from ..database import get_connection
from .amazon_scraper import DEMO_PRODUCTS
from .product_repository import get_product_by_asin, resolve_product_url

HISTORY_LIMIT = 120
TREND_WINDOWS = (3, 7, 30)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _estimate_sales(
    *,
    review_count: int | None,
    rating: float | None,
    source_rank: int | None,
) -> int:
    reviews = int(review_count or 0)
    rating_value = float(rating or 0)
    rank = int(source_rank or 180)
    rank_bonus = max(0, 180 - min(rank, 180)) * 4
    rating_bonus = max(0.0, rating_value - 3.5) * 60
    return max(0, int(round(reviews * 3.2 + rank_bonus + rating_bonus)))


def _product_snapshot(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "price": _coerce_float(product.get("price")),
        "currency": str(product.get("currency") or "USD"),
        "rating": _coerce_float(product.get("rating")),
        "review_count": _coerce_int(product.get("review_count")),
        "estimated_sales": _estimate_sales(
            review_count=_coerce_int(product.get("review_count")),
            rating=_coerce_float(product.get("rating")),
            source_rank=_coerce_int(product.get("source_rank")),
        ),
        "opportunity_score": _coerce_int(product.get("opportunity_score")) or 0,
        "source_rank": _coerce_int(product.get("source_rank")),
        "is_prime": bool(product.get("is_prime")),
        "is_sponsored": bool(product.get("is_sponsored")),
        "availability": str(product.get("availability") or ""),
    }


def _row_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "price": _coerce_float(row.get("latest_price")),
        "currency": str(row.get("latest_currency") or "USD"),
        "rating": _coerce_float(row.get("latest_rating")),
        "review_count": _coerce_int(row.get("latest_review_count")),
        "estimated_sales": _coerce_int(row.get("latest_estimated_sales")) or 0,
        "opportunity_score": _coerce_int(row.get("latest_opportunity_score")) or 0,
        "source_rank": _coerce_int(row.get("latest_source_rank")),
        "is_prime": bool(row.get("latest_is_prime")),
        "is_sponsored": bool(row.get("latest_is_sponsored")),
        "availability": str(row.get("latest_availability") or ""),
    }


def _apply_competitor_metrics(
    connection,
    *,
    competitor_id: int,
    product: dict[str, Any],
    product_url: str,
    checked_at: str,
) -> None:
    snapshot = _product_snapshot(product)
    connection.execute(
        """
        UPDATE competitors
        SET title = ?, product_url = ?, image_url = ?, keyword_hint = ?,
            latest_price = ?, latest_currency = ?, latest_rating = ?, latest_review_count = ?,
            latest_estimated_sales = ?, latest_opportunity_score = ?, latest_source_rank = ?,
            latest_is_prime = ?, latest_is_sponsored = ?, latest_availability = ?,
            source_product_id = ?, last_checked_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            str(product.get("title") or ""),
            product_url,
            str(product.get("image_url") or ""),
            str(product.get("keyword") or ""),
            snapshot["price"],
            snapshot["currency"],
            snapshot["rating"],
            snapshot["review_count"],
            snapshot["estimated_sales"],
            snapshot["opportunity_score"],
            snapshot["source_rank"],
            int(snapshot["is_prime"]),
            int(snapshot["is_sponsored"]),
            snapshot["availability"],
            product.get("id"),
            checked_at,
            checked_at,
            competitor_id,
        ),
    )
    _insert_snapshot(
        connection,
        competitor_id=competitor_id,
        sampled_at=checked_at,
        snapshot=snapshot,
    )


def _insert_snapshot(
    connection,
    *,
    competitor_id: int,
    sampled_at: str,
    snapshot: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO competitor_snapshots (
            competitor_id, sampled_at, price, currency, rating, review_count,
            estimated_sales, opportunity_score, source_rank, is_prime, is_sponsored,
            availability
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            competitor_id,
            sampled_at,
            snapshot.get("price"),
            snapshot.get("currency") or "USD",
            snapshot.get("rating"),
            snapshot.get("review_count"),
            snapshot.get("estimated_sales"),
            snapshot.get("opportunity_score") or 0,
            snapshot.get("source_rank"),
            int(bool(snapshot.get("is_prime"))),
            int(bool(snapshot.get("is_sponsored"))),
            snapshot.get("availability") or "",
        ),
    )


def _seed_demo_history(connection, *, competitor_id: int, product_record: dict[str, Any]) -> None:
    connection.execute(
        "DELETE FROM competitor_snapshots WHERE competitor_id = ?",
        (competitor_id,),
    )
    base = _product_snapshot(product_record)
    base_price = float(base["price"] or 0)
    base_rating = float(base["rating"] or 0)
    base_reviews = int(base["review_count"] or 0)
    base_rank = int(base["source_rank"] or 18)
    now = _utc_now_dt()
    timeline = [
        {"days": 30, "price_shift": -0.12, "review_shift": -42, "rating_shift": -0.18, "rank_shift": 9, "opp_shift": -12},
        {"days": 24, "price_shift": -0.09, "review_shift": -34, "rating_shift": -0.12, "rank_shift": 7, "opp_shift": -9},
        {"days": 18, "price_shift": -0.06, "review_shift": -27, "rating_shift": -0.08, "rank_shift": 6, "opp_shift": -7},
        {"days": 14, "price_shift": -0.04, "review_shift": -20, "rating_shift": -0.05, "rank_shift": 4, "opp_shift": -5},
        {"days": 10, "price_shift": -0.02, "review_shift": -13, "rating_shift": -0.03, "rank_shift": 3, "opp_shift": -3},
        {"days": 7, "price_shift": 0.01, "review_shift": -9, "rating_shift": 0.0, "rank_shift": 2, "opp_shift": -1},
        {"days": 5, "price_shift": 0.03, "review_shift": -6, "rating_shift": 0.03, "rank_shift": 1, "opp_shift": 2},
        {"days": 3, "price_shift": 0.04, "review_shift": -4, "rating_shift": 0.05, "rank_shift": -1, "opp_shift": 4},
        {"days": 1, "price_shift": 0.02, "review_shift": -1, "rating_shift": 0.04, "rank_shift": -2, "opp_shift": 2},
        {"days": 0, "price_shift": 0.0, "review_shift": 0, "rating_shift": 0.0, "rank_shift": 0, "opp_shift": 0},
    ]

    for point in timeline:
        sampled_at = (now - timedelta(days=point["days"])).isoformat()
        review_count = max(0, base_reviews + point["review_shift"])
        source_rank = max(1, base_rank + point["rank_shift"])
        rating = max(0.0, min(5.0, base_rating + point["rating_shift"]))
        price = round(base_price * (1 + point["price_shift"]), 2) if base_price else None
        opportunity_score = max(1, min(100, int((base["opportunity_score"] or 0) + point["opp_shift"])))
        snapshot = {
            "price": price,
            "currency": base["currency"],
            "rating": rating,
            "review_count": review_count,
            "estimated_sales": _estimate_sales(
                review_count=review_count,
                rating=rating,
                source_rank=source_rank,
            ),
            "opportunity_score": opportunity_score,
            "source_rank": source_rank,
            "is_prime": base["is_prime"],
            "is_sponsored": base["is_sponsored"],
            "availability": base["availability"],
        }
        _insert_snapshot(
            connection,
            competitor_id=competitor_id,
            sampled_at=sampled_at,
            snapshot=snapshot,
        )


def seed_demo_intelligence() -> None:
    now = _utc_now()
    with get_connection() as connection:
        for product in DEMO_PRODUCTS:
            product_record = product.to_record()
            connection.execute(
                """
                INSERT INTO keywords (
                    keyword, marketplace, department, status, priority, note,
                    last_scraped_at, last_result_count, created_at, updated_at
                ) VALUES (?, ?, 'tools', 'active', 3, '', ?, 1, ?, ?)
                ON CONFLICT(keyword, marketplace, department) DO UPDATE SET
                    last_scraped_at = excluded.last_scraped_at,
                    last_result_count = excluded.last_result_count,
                    updated_at = excluded.updated_at
                """,
                (
                    product.keyword,
                    product.marketplace,
                    product.scraped_at,
                    now,
                    now,
                ),
            )

            snapshot = _product_snapshot(product_record)
            connection.execute(
                """
                INSERT INTO competitors (
                    asin, marketplace, title, product_url, image_url, keyword_hint,
                    latest_price, latest_currency, latest_rating, latest_review_count,
                    latest_estimated_sales, latest_opportunity_score, latest_source_rank,
                    latest_is_prime, latest_is_sponsored, latest_availability, watch_status,
                    note, source_product_id, last_checked_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'watching', '', NULL, ?, ?, ?)
                ON CONFLICT(asin, marketplace) DO UPDATE SET
                    title = excluded.title,
                    product_url = excluded.product_url,
                    image_url = excluded.image_url,
                    keyword_hint = excluded.keyword_hint,
                    latest_price = excluded.latest_price,
                    latest_currency = excluded.latest_currency,
                    latest_rating = excluded.latest_rating,
                    latest_review_count = excluded.latest_review_count,
                    latest_estimated_sales = excluded.latest_estimated_sales,
                    latest_opportunity_score = excluded.latest_opportunity_score,
                    latest_source_rank = excluded.latest_source_rank,
                    latest_is_prime = excluded.latest_is_prime,
                    latest_is_sponsored = excluded.latest_is_sponsored,
                    latest_availability = excluded.latest_availability,
                    last_checked_at = excluded.last_checked_at,
                    updated_at = excluded.updated_at
                """,
                (
                    product.asin,
                    product.marketplace,
                    product.title,
                    resolve_product_url(
                        asin=product.asin,
                        marketplace=product.marketplace,
                        title=product.title,
                        keyword=product.keyword,
                        product_url=product.product_url,
                    ),
                    product.image_url,
                    product.keyword,
                    snapshot["price"],
                    snapshot["currency"],
                    snapshot["rating"],
                    snapshot["review_count"],
                    snapshot["estimated_sales"],
                    snapshot["opportunity_score"],
                    snapshot["source_rank"],
                    int(snapshot["is_prime"]),
                    int(snapshot["is_sponsored"]),
                    snapshot["availability"],
                    product.scraped_at,
                    now,
                    now,
                ),
            )
            competitor_row = connection.execute(
                """
                SELECT *
                FROM competitors
                WHERE asin = ? AND marketplace = ?
                """,
                (product.asin, product.marketplace),
            ).fetchone()
            _seed_demo_history(
                connection,
                competitor_id=int(competitor_row["id"]),
                product_record=product_record,
            )


def record_scrape_run(
    *,
    keyword: str,
    marketplace: str,
    department: str,
    scraped_count: int,
    saved_count: int,
    status: str,
    message: str,
) -> None:
    created_at = _utc_now()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO scrape_runs (
                keyword, marketplace, department, scraped_count, saved_count,
                status, message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keyword,
                marketplace,
                department,
                scraped_count,
                saved_count,
                status,
                message,
                created_at,
            ),
        )


def upsert_keyword(
    *,
    keyword: str,
    marketplace: str,
    department: str,
    priority: int,
    note: str,
) -> dict[str, Any]:
    now = _utc_now()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO keywords (
                keyword, marketplace, department, status, priority, note,
                last_scraped_at, last_result_count, created_at, updated_at
            ) VALUES (?, ?, ?, 'active', ?, ?, NULL, 0, ?, ?)
            ON CONFLICT(keyword, marketplace, department) DO UPDATE SET
                priority = excluded.priority,
                note = excluded.note,
                updated_at = excluded.updated_at
            """,
            (keyword, marketplace, department, priority, note.strip(), now, now),
        )

        row = connection.execute(
            """
            SELECT *
            FROM keywords
            WHERE keyword = ? AND marketplace = ? AND department = ?
            """,
            (keyword, marketplace, department),
        ).fetchone()
    return dict(row)


def list_keywords() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM keywords
            ORDER BY priority DESC, updated_at DESC, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def update_keyword(keyword_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    assignments: list[str] = []
    params: dict[str, Any] = {"id": keyword_id, "updated_at": _utc_now()}

    if "status" in payload and payload["status"] is not None:
        assignments.append("status = :status")
        params["status"] = payload["status"]
    if "priority" in payload and payload["priority"] is not None:
        assignments.append("priority = :priority")
        params["priority"] = payload["priority"]
    if "note" in payload and payload["note"] is not None:
        assignments.append("note = :note")
        params["note"] = payload["note"].strip()

    if not assignments:
        return get_keyword(keyword_id)

    assignments.append("updated_at = :updated_at")

    with get_connection() as connection:
        connection.execute(
            f"UPDATE keywords SET {', '.join(assignments)} WHERE id = :id",
            params,
        )
    return get_keyword(keyword_id)


def delete_keyword(keyword_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
    return cursor.rowcount > 0


def clear_keywords() -> int:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM keywords")
    return cursor.rowcount


def mark_keyword_scraped(keyword_id: int, result_count: int) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE keywords
            SET last_scraped_at = ?, last_result_count = ?, updated_at = ?
            WHERE id = ?
            """,
            (_utc_now(), result_count, _utc_now(), keyword_id),
        )


def get_keyword(keyword_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM keywords WHERE id = ?",
            (keyword_id,),
        ).fetchone()
    return dict(row) if row else None


def upsert_competitor(
    *,
    asin: str,
    marketplace: str,
    keyword_hint: str,
    note: str,
) -> dict[str, Any]:
    normalized_asin = asin.strip().upper()
    now = _utc_now()
    product = get_product_by_asin(normalized_asin, marketplace)
    product_url = (
        product["product_url"]
        if product
        else resolve_product_url(
            asin=normalized_asin,
            marketplace=marketplace,
            title="",
            keyword=keyword_hint,
            product_url="",
        )
    )

    snapshot = _product_snapshot(product) if product else {
        "price": None,
        "currency": "USD",
        "rating": None,
        "review_count": None,
        "estimated_sales": 0,
        "opportunity_score": 0,
        "source_rank": None,
        "is_prime": False,
        "is_sponsored": False,
        "availability": "",
    }

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO competitors (
                asin, marketplace, title, product_url, image_url, keyword_hint,
                latest_price, latest_currency, latest_rating, latest_review_count,
                latest_estimated_sales, latest_opportunity_score, latest_source_rank,
                latest_is_prime, latest_is_sponsored, latest_availability, watch_status,
                note, source_product_id, last_checked_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'watching', ?, ?, ?, ?, ?)
            ON CONFLICT(asin, marketplace) DO UPDATE SET
                keyword_hint = excluded.keyword_hint,
                note = excluded.note,
                title = CASE WHEN excluded.title = '' THEN competitors.title ELSE excluded.title END,
                product_url = CASE WHEN excluded.product_url = '' THEN competitors.product_url ELSE excluded.product_url END,
                image_url = CASE WHEN excluded.image_url = '' THEN competitors.image_url ELSE excluded.image_url END,
                latest_price = COALESCE(excluded.latest_price, competitors.latest_price),
                latest_currency = CASE WHEN excluded.latest_currency = '' THEN competitors.latest_currency ELSE excluded.latest_currency END,
                latest_rating = COALESCE(excluded.latest_rating, competitors.latest_rating),
                latest_review_count = COALESCE(excluded.latest_review_count, competitors.latest_review_count),
                latest_estimated_sales = COALESCE(excluded.latest_estimated_sales, competitors.latest_estimated_sales),
                latest_opportunity_score = CASE
                    WHEN excluded.latest_opportunity_score = 0 THEN competitors.latest_opportunity_score
                    ELSE excluded.latest_opportunity_score
                END,
                latest_source_rank = COALESCE(excluded.latest_source_rank, competitors.latest_source_rank),
                latest_is_prime = CASE
                    WHEN excluded.latest_is_prime = 1 THEN 1
                    ELSE competitors.latest_is_prime
                END,
                latest_is_sponsored = CASE
                    WHEN excluded.latest_is_sponsored = 1 THEN 1
                    ELSE competitors.latest_is_sponsored
                END,
                latest_availability = CASE
                    WHEN excluded.latest_availability = '' THEN competitors.latest_availability
                    ELSE excluded.latest_availability
                END,
                source_product_id = COALESCE(excluded.source_product_id, competitors.source_product_id),
                last_checked_at = COALESCE(excluded.last_checked_at, competitors.last_checked_at),
                updated_at = excluded.updated_at
            """,
            (
                normalized_asin,
                marketplace,
                product["title"] if product else "",
                product_url,
                product["image_url"] if product else "",
                keyword_hint.strip(),
                snapshot["price"],
                snapshot["currency"],
                snapshot["rating"],
                snapshot["review_count"],
                snapshot["estimated_sales"],
                snapshot["opportunity_score"],
                snapshot["source_rank"],
                int(snapshot["is_prime"]),
                int(snapshot["is_sponsored"]),
                snapshot["availability"],
                note.strip(),
                product["id"] if product else None,
                now if product else None,
                now,
                now,
            ),
        )

        row = connection.execute(
            """
            SELECT *
            FROM competitors
            WHERE asin = ? AND marketplace = ?
            """,
            (normalized_asin, marketplace),
        ).fetchone()
        competitor_id = int(row["id"])
        if product:
            _insert_snapshot(
                connection,
                competitor_id=competitor_id,
                sampled_at=now,
                snapshot=snapshot,
            )

    return get_competitor(competitor_id) or {}


def _load_snapshots_by_competitor(
    connection,
    competitor_ids: list[int],
) -> dict[int, list[dict[str, Any]]]:
    if not competitor_ids:
        return {}

    placeholders = ", ".join("?" for _ in competitor_ids)
    rows = connection.execute(
        f"""
        SELECT *
        FROM competitor_snapshots
        WHERE competitor_id IN ({placeholders})
        ORDER BY competitor_id ASC, sampled_at ASC, id ASC
        """,
        competitor_ids,
    ).fetchall()

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        item = dict(row)
        item["is_prime"] = bool(item["is_prime"])
        item["is_sponsored"] = bool(item["is_sponsored"])
        grouped[int(item["competitor_id"])].append(item)

    for competitor_id, items in grouped.items():
        grouped[competitor_id] = items[-HISTORY_LIMIT:]
    return grouped


def _build_delta(current: Any, previous: Any) -> float | int | None:
    if current is None or previous is None:
        return None
    delta = current - previous
    if isinstance(current, float) or isinstance(previous, float):
        return round(float(delta), 2)
    return int(delta)


def _build_competitor_insights(
    competitor: dict[str, Any],
    current: dict[str, Any],
    previous: dict[str, Any] | None,
) -> list[str]:
    insights: list[str] = []
    if previous:
        review_delta = _build_delta(current.get("review_count"), previous.get("review_count"))
        if review_delta and review_delta > 0:
            insights.append(f"评论数较上次增加 {review_delta}")

        price_delta = _build_delta(current.get("price"), previous.get("price"))
        if price_delta:
            if price_delta < 0:
                insights.append(f"价格下降 {abs(price_delta):.2f}，可能在促销")
            elif price_delta > 0:
                insights.append(f"价格上调 {price_delta:.2f}，利润空间可能回升")

        previous_rank = previous.get("source_rank")
        current_rank = current.get("source_rank")
        if previous_rank is not None and current_rank is not None:
            rank_change = previous_rank - current_rank
            if rank_change >= 2:
                insights.append(f"搜索排名提升 {rank_change} 位")
            elif rank_change <= -2:
                insights.append(f"搜索排名下降 {abs(rank_change)} 位")

    if competitor.get("latest_is_prime"):
        insights.append("Prime 商品，履约优势明显")
    if competitor.get("latest_is_sponsored"):
        insights.append("当前带 Sponsored 标记，广告介入较强")
    if competitor.get("latest_opportunity_score", 0) >= 70:
        insights.append("机会分较高，值得优先跟进")
    return insights[:4]


def _trend_values(history: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    return [
        {"sampled_at": item["sampled_at"], "value": item.get(key)}
        for item in history
        if item.get(key) is not None
    ]


def _history_in_window(history: list[dict[str, Any]], days: int) -> list[dict[str, Any]]:
    if not history:
        return []

    latest_dt = _parse_iso_datetime(history[-1]["sampled_at"])
    if latest_dt is None:
        return history

    cutoff = latest_dt - timedelta(days=days)
    filtered = [
        item
        for item in history
        if (_parse_iso_datetime(item["sampled_at"]) or latest_dt) >= cutoff
    ]
    if not filtered:
        return [history[-1]]
    if filtered[0] is not history[0] and len(filtered) == 1 and len(history) >= 2:
        return [history[-2], history[-1]]
    return filtered


def _build_window_package(history: list[dict[str, Any]], days: int) -> dict[str, Any]:
    window_history = _history_in_window(history, days)
    latest_snapshot = window_history[-1] if window_history else None
    baseline_snapshot = window_history[0] if window_history else None
    return {
        "days": days,
        "sample_count": len(window_history),
        "range_start": baseline_snapshot["sampled_at"] if baseline_snapshot else None,
        "range_end": latest_snapshot["sampled_at"] if latest_snapshot else None,
        "trends": {
            "price": _trend_values(window_history, "price"),
            "rating": _trend_values(window_history, "rating"),
            "review_count": _trend_values(window_history, "review_count"),
            "estimated_sales": _trend_values(window_history, "estimated_sales"),
            "opportunity_score": _trend_values(window_history, "opportunity_score"),
        },
        "deltas": {
            "price": _build_delta(
                latest_snapshot.get("price") if latest_snapshot else None,
                baseline_snapshot.get("price") if baseline_snapshot else None,
            ),
            "rating": _build_delta(
                latest_snapshot.get("rating") if latest_snapshot else None,
                baseline_snapshot.get("rating") if baseline_snapshot else None,
            ),
            "review_count": _build_delta(
                latest_snapshot.get("review_count") if latest_snapshot else None,
                baseline_snapshot.get("review_count") if baseline_snapshot else None,
            ),
            "estimated_sales": _build_delta(
                latest_snapshot.get("estimated_sales") if latest_snapshot else None,
                baseline_snapshot.get("estimated_sales") if baseline_snapshot else None,
            ),
            "opportunity_score": _build_delta(
                latest_snapshot.get("opportunity_score") if latest_snapshot else None,
                baseline_snapshot.get("opportunity_score") if baseline_snapshot else None,
            ),
            "source_rank": _build_delta(
                latest_snapshot.get("source_rank") if latest_snapshot else None,
                baseline_snapshot.get("source_rank") if baseline_snapshot else None,
            ),
        },
    }


def _enrich_competitor(
    row: dict[str, Any],
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    data = _competitor_row_to_dict(row)
    latest_snapshot = history[-1] if history else _row_snapshot(data)
    previous_snapshot = history[-2] if len(history) >= 2 else None

    data["history"] = history
    data["snapshot_count"] = len(history)
    data["latest_is_prime"] = bool(data.get("latest_is_prime"))
    data["latest_is_sponsored"] = bool(data.get("latest_is_sponsored"))
    data["trends"] = {
        "price": _trend_values(history, "price"),
        "rating": _trend_values(history, "rating"),
        "review_count": _trend_values(history, "review_count"),
        "estimated_sales": _trend_values(history, "estimated_sales"),
        "opportunity_score": _trend_values(history, "opportunity_score"),
    }
    data["trend_windows"] = {
        str(days): _build_window_package(history, days)
        for days in TREND_WINDOWS
    }
    data["deltas"] = {
        "price": _build_delta(latest_snapshot.get("price"), previous_snapshot.get("price") if previous_snapshot else None),
        "rating": _build_delta(latest_snapshot.get("rating"), previous_snapshot.get("rating") if previous_snapshot else None),
        "review_count": _build_delta(
            latest_snapshot.get("review_count"),
            previous_snapshot.get("review_count") if previous_snapshot else None,
        ),
        "estimated_sales": _build_delta(
            latest_snapshot.get("estimated_sales"),
            previous_snapshot.get("estimated_sales") if previous_snapshot else None,
        ),
        "opportunity_score": _build_delta(
            latest_snapshot.get("opportunity_score"),
            previous_snapshot.get("opportunity_score") if previous_snapshot else None,
        ),
        "source_rank": _build_delta(
            latest_snapshot.get("source_rank"),
            previous_snapshot.get("source_rank") if previous_snapshot else None,
        ),
    }
    data["insights"] = _build_competitor_insights(data, latest_snapshot, previous_snapshot)
    return data


def list_competitors() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = [
            dict(row)
            for row in connection.execute(
                """
                SELECT *
                FROM competitors
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()
        ]
        snapshots = _load_snapshots_by_competitor(
            connection,
            [int(row["id"]) for row in rows],
        )

    return [
        _enrich_competitor(row, snapshots.get(int(row["id"]), []))
        for row in rows
    ]


def update_competitor(competitor_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    assignments: list[str] = []
    params: dict[str, Any] = {"id": competitor_id, "updated_at": _utc_now()}

    if "watch_status" in payload and payload["watch_status"] is not None:
        assignments.append("watch_status = :watch_status")
        params["watch_status"] = payload["watch_status"]
    if "note" in payload and payload["note"] is not None:
        assignments.append("note = :note")
        params["note"] = payload["note"].strip()

    if not assignments:
        return get_competitor(competitor_id)

    assignments.append("updated_at = :updated_at")
    with get_connection() as connection:
        connection.execute(
            f"UPDATE competitors SET {', '.join(assignments)} WHERE id = :id",
            params,
        )
    return get_competitor(competitor_id)


def delete_competitor(competitor_id: int) -> bool:
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM competitor_snapshots WHERE competitor_id = ?",
            (competitor_id,),
        )
        cursor = connection.execute("DELETE FROM competitors WHERE id = ?", (competitor_id,))
    return cursor.rowcount > 0


def clear_competitors() -> int:
    with get_connection() as connection:
        connection.execute("DELETE FROM competitor_snapshots")
        cursor = connection.execute("DELETE FROM competitors")
    return cursor.rowcount


def get_competitor(competitor_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM competitors WHERE id = ?",
            (competitor_id,),
        ).fetchone()
        if not row:
            return None
        snapshots = _load_snapshots_by_competitor(connection, [competitor_id])
    return _enrich_competitor(dict(row), snapshots.get(competitor_id, []))


def refresh_competitors() -> dict[str, int]:
    updated = 0
    missing = 0
    now = _utc_now()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, asin, marketplace FROM competitors"
        ).fetchall()
        for row in rows:
            product = get_product_by_asin(str(row["asin"]).upper(), row["marketplace"])
            if not product:
                missing += 1
                continue

            product_url = resolve_product_url(
                asin=str(product.get("asin") or row["asin"]),
                marketplace=str(product.get("marketplace") or row["marketplace"]),
                title=str(product.get("title") or ""),
                keyword=str(product.get("keyword") or ""),
                product_url=str(product.get("product_url") or ""),
            )
            _apply_competitor_metrics(
                connection,
                competitor_id=int(row["id"]),
                product=product,
                product_url=product_url,
                checked_at=now,
            )
            updated += 1
    return {"updated": updated, "missing": missing}


def clear_scrape_runs() -> int:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM scrape_runs")
    return cursor.rowcount


def get_dashboard_summary() -> dict[str, Any]:
    with get_connection() as connection:
        product_total = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        favorite_total = connection.execute(
            "SELECT COUNT(*) FROM products WHERE is_favorite = 1"
        ).fetchone()[0]
        keyword_total = connection.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]
        active_keyword_total = connection.execute(
            "SELECT COUNT(*) FROM keywords WHERE status = 'active'"
        ).fetchone()[0]
        competitor_total = connection.execute(
            "SELECT COUNT(*) FROM competitors WHERE watch_status != 'archived'"
        ).fetchone()[0]
        avg_price = connection.execute(
            "SELECT ROUND(AVG(price), 2) FROM products WHERE price IS NOT NULL"
        ).fetchone()[0] or 0
        avg_rating = connection.execute(
            "SELECT ROUND(AVG(rating), 2) FROM products WHERE rating IS NOT NULL"
        ).fetchone()[0] or 0

        top_keywords = [
            dict(row)
            for row in connection.execute(
                """
                SELECT keyword, marketplace, COUNT(*) AS product_count,
                       ROUND(AVG(opportunity_score), 1) AS avg_opportunity_score
                FROM products
                GROUP BY keyword, marketplace
                ORDER BY product_count DESC, avg_opportunity_score DESC
                LIMIT 8
                """
            ).fetchall()
        ]
        status_breakdown = [
            dict(row)
            for row in connection.execute(
                """
                SELECT custom_status AS label, COUNT(*) AS count
                FROM products
                GROUP BY custom_status
                ORDER BY count DESC
                """
            ).fetchall()
        ]
        recent_runs = [
            dict(row)
            for row in connection.execute(
                """
                SELECT keyword, marketplace, scraped_count, saved_count, status, message, created_at
                FROM scrape_runs
                ORDER BY id DESC
                LIMIT 6
                """
            ).fetchall()
        ]

    return {
        "totals": {
            "products": product_total,
            "favorites": favorite_total,
            "keywords": keyword_total,
            "active_keywords": active_keyword_total,
            "competitors": competitor_total,
            "avg_price": avg_price,
            "avg_rating": avg_rating,
        },
        "top_keywords": top_keywords,
        "status_breakdown": status_breakdown,
        "recent_runs": recent_runs,
    }


def _competitor_row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    data["latest_is_prime"] = bool(data.get("latest_is_prime"))
    data["latest_is_sponsored"] = bool(data.get("latest_is_sponsored"))
    data["product_url"] = resolve_product_url(
        asin=str(data.get("asin") or ""),
        marketplace=str(data.get("marketplace") or "com"),
        title=str(data.get("title") or ""),
        keyword=str(data.get("keyword_hint") or ""),
        product_url=str(data.get("product_url") or ""),
    )
    return data
