import pytest
from unittest.mock import AsyncMock, MagicMock
from dereel.crawlers.gog import GogCrawler
from dereel.models.price_result import PriceResult

# ── Mock API 응답 ─────────────────────────────────────────────────────────────
def _make_catalog_response(products: list) -> dict:
    return {
        "products": products,
        "currentlyShownProductCount": len(products),
    }

PRODUCT_WITCHER = {
    "id": 1207664663,
    "title": "The Witcher 3: Wild Hunt",
    "slug": "the_witcher_3_wild_hunt",
    "price": {
        "final": "$9.99",
        "base": "$39.99",
        "finalMoney": {"amount": "9.99",  "currency": "USD"},
        "baseMoney":  {"amount": "39.99", "currency": "USD"},
    },
}

PRODUCT_FREE = {
    "id": 1207664997,
    "title": "Gwent: The Witcher Card Game",
    "slug": "gwent_the_witcher_card_game",
    "price": None,   # 무료 게임
}

MOCK_PRODUCTS = [
    {"slug": "the_witcher_3_wild_hunt", "name": "The Witcher 3", "target_price": 9.99},
]

MOCK_FREE_PRODUCTS = [
    {"slug": "gwent_the_witcher_card_game", "name": "Gwent", "target_price": 0},
]


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture
async def crawler():
    async with GogCrawler() as c:
        yield c


# ── fetch_products() 테스트 ───────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_fetch_returns_price_result(crawler):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = _make_catalog_response([PRODUCT_WITCHER])

    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products(MOCK_PRODUCTS, currency="USD")

    assert len(results) == 1
    assert isinstance(results[0], PriceResult)
    assert results[0].site == "gog"
    assert results[0].product_id == "1207664663"
    assert results[0].original_price == 39.99
    assert results[0].current_price == 9.99
    assert results[0].currency == "USD"
    assert not results[0].is_free


@pytest.mark.asyncio
async def test_fetch_detects_free_game(crawler):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = _make_catalog_response([PRODUCT_FREE])

    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products(MOCK_FREE_PRODUCTS, currency="USD")

    assert len(results) == 1
    assert results[0].is_free
    assert results[0].current_price == 0.0


@pytest.mark.asyncio
async def test_fetch_returns_empty_when_slug_not_matched(crawler):
    """응답 products에 요청한 slug가 없으면 빈 리스트를 반환한다."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    # 전혀 다른 slug의 상품만 반환
    mock_resp.json.return_value = _make_catalog_response([PRODUCT_FREE])

    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products(MOCK_PRODUCTS, currency="USD")  # witcher 3 slug 요청

    assert results == []


@pytest.mark.asyncio
async def test_fetch_returns_empty_on_http_error(crawler):
    """HTTP 오류 시 빈 리스트를 반환한다 (에러를 삼킴)."""
    import httpx
    crawler._client.get = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "503", request=MagicMock(), response=MagicMock(status_code=503)
        )
    )

    results = await crawler.fetch_products(MOCK_PRODUCTS, currency="USD")

    assert results == []


# ── PriceResult 로직 테스트 ───────────────────────────────────────────────────
def test_should_notify_when_below_target():
    result = PriceResult(
        site="gog", product_id="1", name="Test",
        original_price=39.99, current_price=9.99,
        currency="USD", url="https://gog.com/game/test",
    )
    assert result.should_notify(target_price=9.99) is True
    assert result.should_notify(target_price=9.98) is False


def test_should_notify_free_always_true():
    result = PriceResult(
        site="gog", product_id="1", name="Free",
        original_price=0, current_price=0,
        currency="USD", url="https://gog.com/game/free",
    )
    assert result.should_notify(target_price=99.99) is True


# ── format_message() 테스트 ───────────────────────────────────────────────────
def test_format_message_on_sale():
    from datetime import datetime, timezone
    crawler = GogCrawler()
    result = PriceResult(
        site="gog", product_id="1207664663", name="The Witcher 3",
        original_price=39.99, current_price=9.99,
        currency="USD", url="https://www.gog.com/game/the_witcher_3_wild_hunt",
        fetched_at=datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc),
    )
    msg = crawler.format_message(result, target_price=9.99)

    assert "Witcher 3" in msg
    assert "9.99" in msg
    assert "39.99" in msg
    assert "GOG" in msg
    assert "75%" in msg   # 할인율


def test_format_message_free():
    crawler = GogCrawler()
    result = PriceResult(
        site="gog", product_id="1", name="Gwent",
        original_price=0, current_price=0,
        currency="USD", url="https://www.gog.com/game/gwent",
    )
    msg = crawler.format_message(result, target_price=0)
    assert "무료" in msg


# ── 클래스 변수 검증 ──────────────────────────────────────────────────────────
def test_site_name_class_variable():
    assert GogCrawler.site_name == "gog"