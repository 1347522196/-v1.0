from __future__ import annotations

import random
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

from ..config import settings


PRICE_RE = re.compile(r"([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)")
RATING_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)")
REVIEW_LABEL_RE = re.compile(r"([0-9][0-9,]*)\s+ratings?", re.IGNORECASE)
RATING_LABEL_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s+out of 5 stars", re.IGNORECASE)
MONTHLY_BOUGHT_RE = re.compile(
    r"([0-9]+(?:\.[0-9]+)?)\s*([kK])?\+?\s+bought in past month",
    re.IGNORECASE,
)
AUTOMATED_ACCESS_HINT = "to discuss automated access to amazon data"
COOKIE_CACHE: dict[str, dict[str, str]] = {}


@dataclass
class ScrapedProduct:
    asin: str
    marketplace: str
    keyword: str
    title: str
    product_url: str
    image_url: str
    price: float | None
    currency: str
    rating: float | None
    review_count: int | None
    badge: str
    is_prime: bool
    is_sponsored: bool
    availability: str
    scraped_at: str
    brand: str = ""
    category_path: str = "Hardware > Tools"
    source_rank: int | None = None
    estimated_monthly_bought: int | None = None
    opportunity_score: int | None = None

    def to_record(self) -> dict:
        return asdict(self)


DEMO_PRODUCTS: list[ScrapedProduct] = [
    ScrapedProduct(
        asin="B0DEMO001",
        marketplace="com",
        keyword="wrench",
        title="Heavy Duty Adjustable Wrench Set",
        product_url="https://www.amazon.com/dp/B0DEMO001",
        image_url="https://images-na.ssl-images-amazon.com/images/I/61demo1.jpg",
        price=29.99,
        currency="USD",
        rating=4.7,
        review_count=326,
        badge="Amazon's Choice",
        is_prime=True,
        is_sponsored=False,
        availability="In Stock",
        scraped_at="2026-05-05T00:00:00+00:00",
        brand="Heavy",
        source_rank=1,
        estimated_monthly_bought=1200,
        opportunity_score=72,
    ),
    ScrapedProduct(
        asin="B0DEMO002",
        marketplace="com",
        keyword="drill",
        title="Cordless Power Drill Driver Kit",
        product_url="https://www.amazon.com/dp/B0DEMO002",
        image_url="https://images-na.ssl-images-amazon.com/images/I/61demo2.jpg",
        price=89.5,
        currency="USD",
        rating=4.5,
        review_count=1184,
        badge="Best Seller",
        is_prime=True,
        is_sponsored=True,
        availability="In Stock",
        scraped_at="2026-05-05T00:00:00+00:00",
        brand="Cordless",
        source_rank=2,
        estimated_monthly_bought=3200,
        opportunity_score=58,
    ),
    ScrapedProduct(
        asin="B0DEMO003",
        marketplace="com",
        keyword="screwdriver",
        title="Precision Screwdriver Bit Set 58-in-1",
        product_url="https://www.amazon.com/dp/B0DEMO003",
        image_url="https://images-na.ssl-images-amazon.com/images/I/61demo3.jpg",
        price=24.99,
        currency="USD",
        rating=4.3,
        review_count=92,
        badge="",
        is_prime=False,
        is_sponsored=False,
        availability="In Stock",
        scraped_at="2026-05-05T00:00:00+00:00",
        brand="Precision",
        source_rank=1,
        estimated_monthly_bought=180,
        opportunity_score=79,
    ),
]


class AmazonScraper:
    def __init__(self, timeout: int | None = None) -> None:
        self.timeout = timeout or settings.request_timeout_seconds
        self.retry_attempts = max(1, settings.scraper_retry_attempts)
        self.retry_backoff_seconds = max(0.5, settings.scraper_retry_backoff_seconds)
        self.delay_jitter_seconds = max(0.0, settings.scraper_delay_jitter_seconds)
        self._warmed_marketplaces: set[str] = set()
        self.last_warning: str = ""
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": settings.user_agent,
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
            }
        )

    def scrape_search_results(
        self,
        keyword: str,
        marketplace: str,
        max_pages: int = 6,
        department: str = "",
        target_products: int = 100,
        delay_seconds: float | None = None,
    ) -> list[dict]:
        delay = settings.scraper_delay_seconds if delay_seconds is None else delay_seconds
        self.last_warning = ""
        results: list[dict] = []
        next_url = self._build_search_url(
            keyword=keyword,
            marketplace=marketplace,
            department=department,
        )
        source_rank = 1
        self._load_cached_cookies(marketplace)
        self._warmup_marketplace(marketplace)

        for _ in range(max_pages):
            if not next_url:
                break

            try:
                response = self._fetch_search_page(next_url, marketplace=marketplace)
            except Exception as exc:
                if results:
                    self.last_warning = (
                        f"后续分页抓取被中断，已保留前面 {len(results)} 条结果。原因：{exc}"
                    )
                    break
                raise

            try:
                page_products, next_url = self._parse_search_page(
                    html=response.text,
                    keyword=keyword,
                    marketplace=marketplace,
                    base_url=f"https://www.amazon.{marketplace}",
                    start_rank=source_rank,
                )
            except Exception as exc:
                if results:
                    self.last_warning = (
                        f"后续分页解析被中断，已保留前面 {len(results)} 条结果。原因：{exc}"
                    )
                    break
                raise
            results.extend(product.to_record() for product in page_products)
            source_rank += len(page_products)
            self._store_cached_cookies(marketplace)

            if len(results) >= target_products:
                break

            if next_url and delay > 0:
                self._sleep_with_jitter(delay)

        return results[:target_products]

    def _load_cached_cookies(self, marketplace: str) -> None:
        cached = COOKIE_CACHE.get(marketplace) or {}
        if not cached:
            return
        for name, value in cached.items():
            self.session.cookies.set(name, value, domain=f".amazon.{marketplace}", path="/")

    def _store_cached_cookies(self, marketplace: str) -> None:
        relevant = {}
        for cookie in self.session.cookies:
            if f"amazon.{marketplace}" in cookie.domain:
                relevant[cookie.name] = cookie.value
        if relevant:
            COOKIE_CACHE[marketplace] = relevant

    def _warmup_marketplace(self, marketplace: str) -> None:
        if marketplace in self._warmed_marketplaces:
            return

        homepage = f"https://www.amazon.{marketplace}/"
        try:
            response = self.session.get(
                homepage,
                timeout=self.timeout,
                headers={"Referer": homepage},
            )
            if response.ok:
                self._store_cached_cookies(marketplace)
                self._warmed_marketplaces.add(marketplace)
                self._sleep_with_jitter(0.8)
        except requests.RequestException:
            # Warmup is best-effort only; search requests still proceed.
            return

    def _fetch_search_page(self, url: str, *, marketplace: str) -> requests.Response:
        homepage = f"https://www.amazon.{marketplace}/"
        last_error: Exception | None = None

        for attempt in range(1, self.retry_attempts + 1):
            if attempt > 1:
                wait_seconds = self.retry_backoff_seconds * attempt
                self._sleep_with_jitter(wait_seconds)

            try:
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    headers={"Referer": homepage},
                )
                response.raise_for_status()
                return response
            except requests.HTTPError as exc:
                last_error = exc
                response = exc.response
                status_code = response.status_code if response is not None else None
                if status_code in {429, 500, 502, 503, 504} and attempt < self.retry_attempts:
                    continue
                raise self._build_http_runtime_error(exc) from exc
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.retry_attempts:
                    continue
                raise RuntimeError(f"请求亚马逊时网络异常：{exc}") from exc

        if last_error:
            raise RuntimeError(str(last_error)) from last_error
        raise RuntimeError("请求亚马逊失败，未收到可用响应。")

    def _build_http_runtime_error(self, exc: requests.HTTPError) -> RuntimeError:
        response = exc.response
        status_code = response.status_code if response is not None else None
        response_text = response.text.lower() if response is not None and response.text else ""
        if status_code == 503:
            if AUTOMATED_ACCESS_HINT in response_text:
                return RuntimeError(
                    "亚马逊直接返回了 automated access 拦截页。当前请求被明确识别为自动化访问。"
                    " 建议降低采集数量、延长操作间隔，并先在浏览器里正常访问一次对应站点。"
                )
            return RuntimeError(
                "亚马逊返回了 503 Service Unavailable。通常是当前 IP、请求频率或请求指纹触发了限制。"
                " 建议降低采集数量、稍后重试，或换一条更干净的网络。"
            )
        if status_code == 429:
            return RuntimeError("亚马逊返回了 429 Too Many Requests，请降低采集频率后再试。")
        if status_code == 403:
            return RuntimeError("亚马逊返回了 403 Forbidden，当前请求大概率已被站点拒绝。")
        if status_code in {500, 502, 504}:
            return RuntimeError(
                f"亚马逊返回了 {status_code} 服务器错误。程序已自动重试，但当前仍未恢复，请稍后再试。"
            )
        detail = str(exc)
        return RuntimeError(f"亚马逊请求失败：{detail}")

    def _sleep_with_jitter(self, base_seconds: float) -> None:
        if base_seconds <= 0:
            return
        jitter = random.uniform(0, self.delay_jitter_seconds) if self.delay_jitter_seconds else 0.0
        time.sleep(base_seconds + jitter)

    def _build_search_url(self, keyword: str, marketplace: str, department: str) -> str:
        params = {"k": keyword}
        if department.strip():
            params["i"] = department.strip()
        query = urlencode(params)
        return f"https://www.amazon.{marketplace}/s?{query}"

    def _parse_search_page(
        self,
        html: str,
        keyword: str,
        marketplace: str,
        base_url: str,
        start_rank: int,
    ) -> tuple[list[ScrapedProduct], str | None]:
        lower_html = html.lower()
        if "captcha" in lower_html or "enter the characters you see below" in lower_html:
            raise RuntimeError("亚马逊返回了验证码页面，当前请求被拦截，请稍后重试。")
        if (
            "awswafintegration" in lower_html
            or "we need to verify that you're not a robot" in lower_html
            or "challenge-container" in lower_html
            or ("javascript is disabled" in lower_html and "not a robot" in lower_html)
        ):
            raise RuntimeError("亚马逊返回了机器人验证页，当前站点暂时无法直接采集，请换站点或稍后再试。")

        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("div[data-component-type='s-search-result']")
        if not cards:
            raise RuntimeError("没有在结果页中解析到商品卡片，可能是页面结构变化或请求被限制。")

        products: list[ScrapedProduct] = []
        scraped_at = datetime.now(timezone.utc).isoformat()

        for offset, card in enumerate(cards):
            asin = (card.get("data-asin") or "").strip()
            if not asin:
                continue

            title_element = (
                card.select_one("[data-cy='title-recipe'] h2 span")
                or card.select_one("h2 span")
                or card.select_one("a[href*='/dp/'] span")
            )
            link_element = (
                card.select_one("[data-cy='title-recipe'] a[href]")
                or card.select_one("a.a-link-normal.s-no-outline[href*='/dp/']")
                or card.select_one("a[href*='/dp/']")
            )
            if not title_element or not link_element:
                continue

            title = self._clean_text(title_element.get_text(" ", strip=True))
            product_url = urljoin(base_url, link_element.get("href", ""))
            image_node = card.select_one("img.s-image")
            image_url = image_node.get("src", "") if image_node else ""
            price, currency = self._extract_price(card)
            rating = self._extract_rating(card)
            review_count = self._extract_review_count(card)
            estimated_monthly_bought = self._extract_monthly_bought(card)
            badge_node = card.select_one(".a-badge-label-inner")
            badge = self._clean_text(badge_node.get_text(" ", strip=True) if badge_node else "")
            availability_node = card.select_one(".a-color-price")
            availability = self._clean_text(
                availability_node.get_text(" ", strip=True) if availability_node else ""
            )
            full_text = card.get_text(" ", strip=True).lower()
            is_prime = bool(card.select_one("[aria-label='Amazon Prime']")) or "prime" in full_text
            is_sponsored = "sponsored" in full_text

            products.append(
                ScrapedProduct(
                    asin=asin,
                    marketplace=marketplace,
                    keyword=keyword,
                    title=title,
                    product_url=product_url,
                    image_url=image_url,
                    price=price,
                    currency=currency,
                    rating=rating,
                    review_count=review_count,
                    badge=badge,
                    is_prime=is_prime,
                    is_sponsored=is_sponsored,
                    availability=availability,
                    scraped_at=scraped_at,
                    brand=self._infer_brand(title),
                    category_path="Hardware > Tools",
                    source_rank=start_rank + offset,
                    estimated_monthly_bought=estimated_monthly_bought,
                )
            )

        next_link = soup.select_one("a.s-pagination-next:not(.s-pagination-disabled)")
        next_url = urljoin(base_url, next_link.get("href")) if next_link else None
        return products, next_url

    def _extract_price(self, card) -> tuple[float | None, str]:
        price_text = ""
        price_node = card.select_one(".a-price .a-offscreen")
        if price_node:
            price_text = price_node.get_text(strip=True)

        if not price_text:
            return None, "USD"

        currency = "USD"
        if "£" in price_text:
            currency = "GBP"
        elif "€" in price_text:
            currency = "EUR"
        elif "¥" in price_text:
            currency = "JPY"

        match = PRICE_RE.search(price_text.replace(",", ""))
        if not match:
            return None, currency

        return float(match.group(1)), currency

    def _extract_rating(self, card) -> float | None:
        for node in card.select("[aria-label]"):
            label = node.get("aria-label", "")
            match = RATING_LABEL_RE.search(label)
            if match:
                return float(match.group(1))

        rating_node = card.select_one("span.a-icon-alt")
        if not rating_node:
            return None

        match = RATING_RE.search(rating_node.get_text(strip=True))
        return float(match.group(1)) if match else None

    def _extract_review_count(self, card) -> int | None:
        candidates: list[str] = []
        candidates.extend(
            node.get_text(strip=True)
            for node in card.select("span.a-size-base.s-underline-text")
        )
        candidates.extend(
            node.get("aria-label", "").strip()
            for node in card.select("[aria-label]")
            if "rating" in node.get("aria-label", "").lower()
        )
        for text in candidates:
            match = REVIEW_LABEL_RE.search(text)
            if match:
                return int(match.group(1).replace(",", ""))
            compact = text.strip()
            if re.fullmatch(r"[0-9][0-9,]{0,10}\+?", compact):
                return int(compact.replace(",", "").replace("+", ""))
        return None

    def _extract_monthly_bought(self, card) -> int | None:
        text = card.get_text(" ", strip=True)
        match = MONTHLY_BOUGHT_RE.search(text)
        if not match:
            return None
        value = float(match.group(1))
        if match.group(2):
            value *= 1000
        return int(value)

    def _clean_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def _infer_brand(self, title: str) -> str:
        words = [part for part in title.split() if part.strip()]
        return words[0][:40] if words else ""
