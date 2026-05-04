import json
import re

from loguru import logger
from playwright.async_api import async_playwright

from dereel.core.base_crawler import BaseCrawler
from dereel.models.stock_result import StockResult

_BOOTSTRAP_RE = re.compile(r"window\.REFURB_GRID_BOOTSTRAP\s*=\s*(\{.+?\});\s*\n", re.DOTALL)


class AppleRefurbCrawler(BaseCrawler):
    """Apple 공식 리퍼비시 스토어 재고 크롤러 (Playwright + Bootstrap JSON)."""

    site_name = "apple_refurb"

    async def __aenter__(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True)
        return self

    async def __aexit__(self, *args):
        await self._browser.close()
        await self._pw.stop()

    async def fetch(self, url: str) -> list[StockResult]:
        logger.info(f"[{self.site_name}] 크롤링 시작 — {url}")
        page = await self._browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=60_000)
            html = await page.content()
        finally:
            await page.close()
        return self._parse(html)

    def _parse(self, html: str) -> list[StockResult]:
        m = _BOOTSTRAP_RE.search(html)
        if not m:
            raise ValueError(
                "REFURB_GRID_BOOTSTRAP 미발견 — 페이지 구조 변경 가능성"
            )

        tiles = json.loads(m.group(1)).get("tiles") or []
        results = []

        for tile in tiles:
            try:
                product_id = tile["partNumber"]
                name = tile["title"]
                url = "https://www.apple.com" + tile["productDetailsUrl"].split("?")[0]
                price = float(tile["price"]["currentPrice"]["raw_amount"])
                currency = tile["price"].get("priceCurrency", "KRW")

                results.append(StockResult(
                    site=self.site_name,
                    product_id=product_id,
                    name=name,
                    url=url,
                    in_stock=True,
                    price=price,
                    currency=currency,
                ))
            except Exception as e:
                logger.warning(f"[{self.site_name}] 타일 파싱 오류 — {e}")
                continue

        logger.info(f"[{self.site_name}] {len(results)}건 파싱 완료")
        return results
