# tests/crawlers/test_apple_refurb.py
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dereel.crawlers.apple_refurb import AppleRefurbCrawler
from dereel.models.stock_result import StockResult

# ── Mock HTML ────────────────────────────────────────────────────────────────
def _make_html(tiles: list) -> str:
    payload = json.dumps({"tiles": tiles})
    return f"<html><script>window.REFURB_GRID_BOOTSTRAP = {payload};\n</script></html>"


TILE_AIRPODS_PRO = {
    "partNumber": "MQTP3KH/A",
    "title": "Refurbished AirPods Pro (2nd generation) with MagSafe Case (USB-C)",
    "productDetailsUrl": "/kr/shop/product/MQTP3KH/A?fnode=1",
    "price": {
        "currentPrice": {"raw_amount": "289000"},
        "priceCurrency": "KRW",
    },
}

TILE_AIRPODS_3RD = {
    "partNumber": "MME73KH/A",
    "title": "Refurbished AirPods (3rd generation)",
    "productDetailsUrl": "/kr/shop/product/MME73KH/A",
    "price": {
        "currentPrice": {"raw_amount": "199000"},
        "priceCurrency": "KRW",
    },
}

TILE_MISSING_PRICE = {
    "partNumber": "BROKEN001",
    "title": "Broken Tile",
    "productDetailsUrl": "/kr/shop/product/BROKEN001",
}

HTML_WITH_STOCK    = _make_html([TILE_AIRPODS_PRO, TILE_AIRPODS_3RD])
HTML_EMPTY         = _make_html([])
HTML_NO_BOOTSTRAP  = "<html><body>Nothing here</body></html>"
HTML_WITH_BAD_TILE = _make_html([TILE_AIRPODS_PRO, TILE_MISSING_PRICE])


# ── Playwright 모킹 헬퍼 ──────────────────────────────────────────────────────
def _make_mock_browser(html: str) -> AsyncMock:
    """html을 반환하는 mock browser를 생성한다."""
    mock_page = AsyncMock()
    mock_page.content = AsyncMock(return_value=html)
    mock_page.goto = AsyncMock()
    mock_page.close = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.close = AsyncMock()
    return mock_browser


def _make_mock_pw(mock_browser: AsyncMock) -> AsyncMock:
    """_browser를 반환하는 mock playwright를 생성한다.

    async_playwright() 호출 흐름:
        pw_instance = await async_playwright().start()   ← .start()가 await 대상
        browser     = await pw_instance.chromium.launch(...)
    """
    mock_pw = AsyncMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_pw.stop = AsyncMock()

    # async_playwright()의 반환값 — .start()가 await 가능해야 함
    mock_ap = MagicMock()
    mock_ap.start = AsyncMock(return_value=mock_pw)
    return mock_ap


# ── _parse() 단위 테스트 ──────────────────────────────────────────────────────
def test_parse_returns_stock_results():
    crawler = AppleRefurbCrawler()
    results = crawler._parse(HTML_WITH_STOCK)

    assert len(results) == 2
    assert all(isinstance(r, StockResult) for r in results)
    assert all(r.site == "apple_refurb" for r in results)
    assert all(r.in_stock is True for r in results)


def test_parse_returns_empty_on_no_tiles():
    crawler = AppleRefurbCrawler()
    assert crawler._parse(HTML_EMPTY) == []


def test_parse_raises_on_missing_bootstrap():
    crawler = AppleRefurbCrawler()
    with pytest.raises(ValueError, match="REFURB_GRID_BOOTSTRAP"):
        crawler._parse(HTML_NO_BOOTSTRAP)


def test_parse_skips_malformed_tile():
    crawler = AppleRefurbCrawler()
    results = crawler._parse(HTML_WITH_BAD_TILE)

    assert len(results) == 1
    assert results[0].product_id == "MQTP3KH/A"


def test_parse_result_fields():
    crawler = AppleRefurbCrawler()
    first = crawler._parse(HTML_WITH_STOCK)[0]

    assert first.product_id == "MQTP3KH/A"
    assert "AirPods Pro" in first.name
    assert first.price == 289000.0
    assert first.currency == "KRW"
    assert first.url == "https://www.apple.com/kr/shop/product/MQTP3KH/A"
    assert first.in_stock is True


def test_parse_strips_query_string_from_url():
    crawler = AppleRefurbCrawler()
    results = crawler._parse(HTML_WITH_STOCK)
    assert "?" not in results[0].url


# ── fetch() 통합 테스트 ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_fetch_calls_playwright_and_returns_results():
    """fetch()가 Playwright로 HTML을 가져와 StockResult를 반환한다."""
    mock_browser = _make_mock_browser(HTML_WITH_STOCK)
    mock_ap      = _make_mock_pw(mock_browser)

    with patch("dereel.crawlers.apple_refurb.async_playwright", return_value=mock_ap):
        async with AppleRefurbCrawler() as crawler:
            results = await crawler.fetch("https://www.apple.com/kr/shop/refurbished/airpods")

    assert len(results) == 2
    assert all(isinstance(r, StockResult) for r in results)


@pytest.mark.asyncio
async def test_fetch_raises_when_bootstrap_missing():
    """Bootstrap JSON이 없으면 ValueError를 raise한다."""
    mock_browser = _make_mock_browser(HTML_NO_BOOTSTRAP)
    mock_ap      = _make_mock_pw(mock_browser)

    with patch("dereel.crawlers.apple_refurb.async_playwright", return_value=mock_ap):
        async with AppleRefurbCrawler() as crawler:
            with pytest.raises(ValueError):
                await crawler.fetch("https://www.apple.com/kr/shop/refurbished/airpods")


# ── 클래스 변수 검증 ──────────────────────────────────────────────────────────
def test_site_name_class_variable():
    assert AppleRefurbCrawler.site_name == "apple_refurb"
