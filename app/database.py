from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import settings


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(settings.database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = _connect()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                marketplace TEXT NOT NULL,
                keyword TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                product_url TEXT NOT NULL,
                image_url TEXT NOT NULL DEFAULT '',
                price REAL,
                currency TEXT NOT NULL DEFAULT 'USD',
                rating REAL,
                review_count INTEGER,
                badge TEXT NOT NULL DEFAULT '',
                is_prime INTEGER NOT NULL DEFAULT 0,
                is_sponsored INTEGER NOT NULL DEFAULT 0,
                availability TEXT NOT NULL DEFAULT '',
                scraped_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_favorite INTEGER NOT NULL DEFAULT 0,
                custom_status TEXT NOT NULL DEFAULT 'new',
                note TEXT NOT NULL DEFAULT '',
                brand TEXT NOT NULL DEFAULT '',
                category_path TEXT NOT NULL DEFAULT '',
                source_rank INTEGER,
                estimated_monthly_bought INTEGER,
                opportunity_score INTEGER NOT NULL DEFAULT 0,
                UNIQUE (asin, marketplace)
            )
            """
        )
        _ensure_columns(
            connection,
            "products",
            {
                "brand": "TEXT NOT NULL DEFAULT ''",
                "category_path": "TEXT NOT NULL DEFAULT ''",
                "source_rank": "INTEGER",
                "estimated_monthly_bought": "INTEGER",
                "opportunity_score": "INTEGER NOT NULL DEFAULT 0",
            },
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                marketplace TEXT NOT NULL,
                department TEXT NOT NULL DEFAULT 'tools',
                status TEXT NOT NULL DEFAULT 'active',
                priority INTEGER NOT NULL DEFAULT 3,
                note TEXT NOT NULL DEFAULT '',
                last_scraped_at TEXT,
                last_result_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (keyword, marketplace, department)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS competitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                marketplace TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                product_url TEXT NOT NULL DEFAULT '',
                image_url TEXT NOT NULL DEFAULT '',
                keyword_hint TEXT NOT NULL DEFAULT '',
                latest_price REAL,
                latest_currency TEXT NOT NULL DEFAULT 'USD',
                latest_rating REAL,
                latest_review_count INTEGER,
                latest_estimated_sales INTEGER,
                latest_opportunity_score INTEGER NOT NULL DEFAULT 0,
                latest_source_rank INTEGER,
                latest_is_prime INTEGER NOT NULL DEFAULT 0,
                latest_is_sponsored INTEGER NOT NULL DEFAULT 0,
                latest_availability TEXT NOT NULL DEFAULT '',
                watch_status TEXT NOT NULL DEFAULT 'watching',
                note TEXT NOT NULL DEFAULT '',
                source_product_id INTEGER,
                last_checked_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (asin, marketplace)
            )
            """
        )
        _ensure_columns(
            connection,
            "competitors",
            {
                "latest_currency": "TEXT NOT NULL DEFAULT 'USD'",
                "latest_estimated_sales": "INTEGER",
                "latest_opportunity_score": "INTEGER NOT NULL DEFAULT 0",
                "latest_source_rank": "INTEGER",
                "latest_is_prime": "INTEGER NOT NULL DEFAULT 0",
                "latest_is_sponsored": "INTEGER NOT NULL DEFAULT 0",
                "latest_availability": "TEXT NOT NULL DEFAULT ''",
            },
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS competitor_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor_id INTEGER NOT NULL,
                sampled_at TEXT NOT NULL,
                price REAL,
                currency TEXT NOT NULL DEFAULT 'USD',
                rating REAL,
                review_count INTEGER,
                estimated_sales INTEGER,
                opportunity_score INTEGER NOT NULL DEFAULT 0,
                source_rank INTEGER,
                is_prime INTEGER NOT NULL DEFAULT 0,
                is_sponsored INTEGER NOT NULL DEFAULT 0,
                availability TEXT NOT NULL DEFAULT ''
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scrape_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                marketplace TEXT NOT NULL,
                department TEXT NOT NULL DEFAULT 'tools',
                scraped_count INTEGER NOT NULL DEFAULT 0,
                saved_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'success',
                message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_products_marketplace
            ON products(marketplace)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_products_title
            ON products(title)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_products_status
            ON products(custom_status)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_keywords_status
            ON keywords(status)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_competitors_status
            ON competitors(watch_status)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_competitor_snapshots_competitor
            ON competitor_snapshots(competitor_id, sampled_at DESC)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_scrape_runs_created
            ON scrape_runs(created_at DESC)
            """
        )


def _ensure_columns(
    connection: sqlite3.Connection,
    table_name: str,
    columns: dict[str, str],
) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, column_sql in columns.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"
            )
