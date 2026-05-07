from __future__ import annotations

from urllib.parse import urlparse

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .runtime import bundle_root
from .schemas import (
    AIAnalyzeRequest,
    AISettingsUpdate,
    ActionResponse,
    CompetitorCreate,
    CompetitorUpdate,
    KeywordCreate,
    KeywordUpdate,
    ProductListResponse,
    ProductUpdate,
    ScrapeRequest,
)
from .services.amazon_scraper import AmazonScraper
from .services.ai_settings import clear_ai_settings, load_ai_settings, save_ai_settings
from .services.deepseek_service import analyze_with_deepseek
from .services.intel_repository import (
    clear_competitors,
    clear_keywords,
    clear_scrape_runs,
    delete_competitor,
    delete_keyword,
    get_competitor,
    get_dashboard_summary,
    get_keyword,
    list_competitors,
    list_keywords,
    mark_keyword_scraped,
    record_scrape_run,
    refresh_competitors,
    seed_demo_intelligence,
    update_competitor,
    update_keyword,
    upsert_competitor,
    upsert_keyword,
)
from .services.product_repository import (
    clear_products,
    delete_product,
    get_product,
    list_products,
    seed_demo_products,
    toggle_favorite,
    update_product,
    upsert_products,
)


STATIC_DIR = bundle_root() / "app" / "static"

app = FastAPI(title="SellerSprite Lite", version="2.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()


def _placeholder_svg(label: str = "Product") -> str:
    safe_label = (label or "Product").strip()[:24]
    text = safe_label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320">
      <defs>
        <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#f2e2cc" />
          <stop offset="100%" stop-color="#d4b089" />
        </linearGradient>
      </defs>
      <rect width="320" height="320" rx="36" fill="url(#g)" />
      <rect x="28" y="28" width="264" height="264" rx="28" fill="rgba(255,255,255,0.55)" />
      <text x="160" y="150" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif"
        font-size="28" font-weight="700" fill="#6f513d">No Image</text>
      <text x="160" y="192" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif"
        font-size="18" fill="#7a604d">{text}</text>
    </svg>
    """.strip()


def _placeholder_response(label: str = "Product") -> Response:
    return Response(content=_placeholder_svg(label), media_type="image/svg+xml")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/image-proxy")
def image_proxy(url: str = Query(default=""), label: str = Query(default="Product")) -> Response:
    if not url:
        return _placeholder_response(label)

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="图片地址格式不正确。")

    try:
        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": settings.user_agent,
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": f"https://www.amazon.{settings.default_marketplace}/",
            },
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            return _placeholder_response(label)
        return Response(content=response.content, media_type=content_type)
    except requests.RequestException:
        return _placeholder_response(label)


@app.get("/api/dashboard")
def dashboard() -> dict:
    return get_dashboard_summary()


@app.get("/api/ai/settings")
def get_ai_settings() -> dict:
    settings_payload = load_ai_settings()
    return {
        "has_api_key": settings_payload["has_api_key"],
        "masked_api_key": settings_payload["masked_api_key"],
        "model": settings_payload["model"],
        "source": settings_payload["source"],
    }


@app.post("/api/ai/settings")
def update_ai_settings(payload: AISettingsUpdate) -> dict:
    settings_payload = save_ai_settings(api_key=payload.api_key, model=payload.model)
    return {
        "message": "AI 设置已写入本次运行，关闭程序后会自动清空。",
        "has_api_key": settings_payload["has_api_key"],
        "masked_api_key": settings_payload["masked_api_key"],
        "model": settings_payload["model"],
        "source": settings_payload["source"],
    }


@app.delete("/api/ai/settings", response_model=ActionResponse)
def delete_ai_settings() -> dict:
    clear_ai_settings()
    return {"message": "AI 设置已清空，本次运行不会再保留 Key。"}


def _recommended_max_pages(target_products: int) -> int:
    estimated_per_page = 16
    return max(1, min(20, (target_products + estimated_per_page - 1) // estimated_per_page))


@app.post("/api/ai/analyze")
def analyze_inventory(payload: AIAnalyzeRequest) -> dict:
    try:
        return analyze_with_deepseek(
            scope=payload.scope,
            user_question=payload.question,
        )
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise HTTPException(status_code=400, detail=f"DeepSeek 调用失败：{detail}") from exc
    except requests.RequestException as exc:
        raise HTTPException(status_code=400, detail=f"DeepSeek 网络请求失败：{exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/products", response_model=ProductListResponse)
def products(
    query: str = Query(default=""),
    marketplace: str = Query(default=""),
    status: str = Query(default=""),
    keyword: str = Query(default=""),
    only_favorites: bool = Query(default=False),
    min_price: float | None = Query(default=None),
    max_price: float | None = Query(default=None),
    sort_by: str = Query(default="comprehensive"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = list_products(
        query=query,
        marketplace=marketplace,
        status=status,
        keyword=keyword,
        only_favorites=only_favorites,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@app.post("/api/demo-seed", response_model=ActionResponse)
def demo_seed() -> dict:
    count = seed_demo_products()
    seed_demo_intelligence()
    return {"message": f"已导入 {count} 条演示商品，并同步了关键词库与竞品库。"}


@app.post("/api/scrape")
def scrape(payload: ScrapeRequest) -> dict:
    search_keyword = payload.keyword.strip()
    if not search_keyword:
        raise HTTPException(status_code=400, detail="关键词不能为空。")
    scraper = AmazonScraper()
    max_pages = payload.max_pages or _recommended_max_pages(payload.target_products)
    try:
        scraped_products = scraper.scrape_search_results(
            keyword=search_keyword,
            marketplace=payload.marketplace,
            max_pages=max_pages,
            department=payload.department,
            target_products=payload.target_products,
            delay_seconds=payload.delay_seconds,
        )
    except Exception as exc:
        record_scrape_run(
            keyword=search_keyword,
            marketplace=payload.marketplace,
            department=payload.department,
            scraped_count=0,
            saved_count=0,
            status="failed",
            message=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    saved = upsert_products(scraped_products)
    keyword_record = upsert_keyword(
        keyword=search_keyword,
        marketplace=payload.marketplace,
        department=payload.department,
        priority=3,
        note="",
    )
    mark_keyword_scraped(keyword_record["id"], len(scraped_products))
    record_scrape_run(
        keyword=search_keyword,
        marketplace=payload.marketplace,
        department=payload.department,
        scraped_count=len(scraped_products),
        saved_count=saved,
        status="success",
        message="采集完成",
    )
    return {
        "message": scraper.last_warning or "采集完成",
        "scraped_count": len(scraped_products),
        "saved_count": saved,
        "keyword": payload.keyword,
        "search_keyword": search_keyword,
        "target_products": payload.target_products,
        "max_pages": max_pages,
        "marketplace": payload.marketplace,
        "warning": scraper.last_warning,
    }


@app.patch("/api/products/{product_id}")
def patch_product(product_id: int, payload: ProductUpdate) -> dict:
    product = update_product(product_id, payload.model_dump())
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在。")
    return product


@app.post("/api/products/{product_id}/favorite")
def favorite_product(product_id: int) -> dict:
    product = toggle_favorite(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在。")
    return product


@app.delete("/api/products/{product_id}", response_model=ActionResponse)
def remove_product(product_id: int) -> dict:
    deleted = delete_product(product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="商品不存在。")
    return {"message": "商品已删除。"}


@app.delete("/api/products", response_model=ActionResponse)
def remove_all_products() -> dict:
    deleted_count = clear_products()
    return {"message": f"已清空商品库，共删除 {deleted_count} 条记录。"}


@app.get("/api/products/{product_id}/open", include_in_schema=False)
def open_product(product_id: int) -> RedirectResponse:
    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在。")
    return RedirectResponse(url=product["product_url"], status_code=307)


@app.get("/api/keywords")
def keywords() -> list[dict]:
    return list_keywords()


@app.post("/api/keywords")
def create_keyword(payload: KeywordCreate) -> dict:
    return upsert_keyword(
        keyword=payload.keyword.strip(),
        marketplace=payload.marketplace,
        department=payload.department,
        priority=payload.priority,
        note=payload.note.strip(),
    )


@app.patch("/api/keywords/{keyword_id}")
def patch_keyword(keyword_id: int, payload: KeywordUpdate) -> dict:
    keyword = update_keyword(keyword_id, payload.model_dump())
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在。")
    return keyword


@app.delete("/api/keywords/{keyword_id}", response_model=ActionResponse)
def remove_keyword(keyword_id: int) -> dict:
    deleted = delete_keyword(keyword_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="关键词不存在。")
    return {"message": "关键词已删除。"}


@app.delete("/api/keywords", response_model=ActionResponse)
def remove_all_keywords() -> dict:
    deleted_count = clear_keywords()
    return {"message": f"已清空关键词库，共删除 {deleted_count} 条记录。"}


@app.post("/api/keywords/{keyword_id}/scrape")
def scrape_keyword(
    keyword_id: int,
    max_pages: int | None = Query(default=None, ge=1, le=20),
    target_products: int = Query(default=100, ge=10, le=200),
) -> dict:
    keyword_record = get_keyword(keyword_id)
    if not keyword_record:
        raise HTTPException(status_code=404, detail="关键词不存在。")

    payload = ScrapeRequest(
        keyword=keyword_record["keyword"],
        marketplace=keyword_record["marketplace"],
        department=keyword_record["department"],
        max_pages=max_pages,
        target_products=target_products,
        delay_seconds=1,
    )
    result = scrape(payload)
    mark_keyword_scraped(keyword_id, result["scraped_count"])
    return result


@app.get("/api/competitors")
def competitors() -> list[dict]:
    return list_competitors()


@app.post("/api/competitors")
def create_competitor(payload: CompetitorCreate) -> dict:
    return upsert_competitor(
        asin=payload.asin,
        marketplace=payload.marketplace,
        keyword_hint=payload.keyword_hint,
        note=payload.note,
    )


@app.patch("/api/competitors/{competitor_id}")
def patch_competitor(competitor_id: int, payload: CompetitorUpdate) -> dict:
    competitor = update_competitor(competitor_id, payload.model_dump())
    if not competitor:
        raise HTTPException(status_code=404, detail="竞品不存在。")
    return competitor


@app.post("/api/competitors/refresh")
def refresh_competitor_snapshots() -> dict:
    stats = refresh_competitors()
    return {
        "message": f"已刷新 {stats['updated']} 个竞品，{stats['missing']} 个竞品暂时没有匹配到商品库数据。",
        **stats,
    }


@app.delete("/api/competitors/{competitor_id}", response_model=ActionResponse)
def remove_competitor(competitor_id: int) -> dict:
    deleted = delete_competitor(competitor_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="竞品不存在。")
    return {"message": "竞品已删除。"}


@app.delete("/api/competitors", response_model=ActionResponse)
def remove_all_competitors() -> dict:
    deleted_count = clear_competitors()
    return {"message": f"已清空竞品库，共删除 {deleted_count} 条记录。"}


@app.get("/api/competitors/{competitor_id}/open", include_in_schema=False)
def open_competitor(competitor_id: int) -> RedirectResponse:
    competitor = get_competitor(competitor_id)
    if not competitor:
        raise HTTPException(status_code=404, detail="竞品不存在。")
    return RedirectResponse(url=competitor["product_url"], status_code=307)


@app.delete("/api/scrape-runs", response_model=ActionResponse)
def remove_all_scrape_runs() -> dict:
    deleted_count = clear_scrape_runs()
    return {"message": f"已清空采集记录，共删除 {deleted_count} 条记录。"}
