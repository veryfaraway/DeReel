# tests/crawlers/test_steam.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, AsyncMock
from dereel.crawlers.steam import SteamCrawler
from dereel.models.price_result import PriceResult


MOCK_CONFIG_PRODUCTS = [
    {"app_id": "1245620", "name": "Elden Ring", "target_price": 33000},
]

MOCK_API_RESPONSE_SALE = {
    "1245620": {
        "success": True,
        "data": {
            "price_overview": {
                "currency": "KRW",
                "initial": 6600000,
                "final": 3300000,
                "discount_percent": 50,
            }
        },
    }
}

MOCK_API_RESPONSE_FREE = {
    "730": {
        "success": True,
        "data": {},  # price_overview 없음 = 무료
    }
}

MOCK_API_RESPONSE_FAIL = {
    "9999": {"success": False}
}


@pytest.fixture
async def crawler():
    """BaseCrawler의 async with 패턴을 따르는 fixture"""
    async with SteamCrawler() as c:
        yield c


@pytest.mark.asyncio
async def test_fetch_returns_price_result_on_sale(crawler):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = MOCK_API_RESPONSE_SALE

    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products(MOCK_CONFIG_PRODUCTS, currency="KRW")

    assert len(results) == 1
    result = results[0]
    assert isinstance(result, PriceResult)
    assert result.site == "steam"
    assert result.product_id == "1245620"
    assert result.original_price == 66000.0
    assert result.current_price == 33000.0
    assert result.currency == "KRW"
    assert not result.is_free


@pytest.mark.asyncio
async def test_fetch_detects_free_game(crawler):
    products = [{"app_id": "730", "name": "CS2", "target_price": 0}]

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = MOCK_API_RESPONSE_FREE

    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products(products, currency="KRW")

    assert len(results) == 1
    assert results[0].is_free
    assert results[0].current_price == 0


@pytest.mark.asyncio
async def test_fetch_returns_empty_on_api_failure(crawler):
    products = [{"app_id": "9999", "name": "Ghost", "target_price": 0}]

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = MOCK_API_RESPONSE_FAIL

    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products(products, currency="KRW")

    assert results == []


def test_should_notify_below_target():
    result = PriceResult(
        site="steam", product_id="1", name="Test",
        original_price=66000, current_price=33000,
        currency="KRW", url="https://example.com"
    )
    assert result.should_notify(target_price=33000) is True
    assert result.should_notify(target_price=32999) is False


def test_should_notify_free_always_true():
    result = PriceResult(
        site="steam", product_id="1", name="Free Game",
        original_price=0, current_price=0,
        currency="KRW", url="https://example.com"
    )
    assert result.should_notify(target_price=99999) is True


def test_format_message_on_sale():
    from datetime import datetime, timezone
    crawler_sync = SteamCrawler()
    result = PriceResult(
        site="steam", product_id="1245620", name="Elden Ring",
        original_price=66000, current_price=33000,
        currency="KRW", url="https://store.steampowered.com/app/1245620",
        fetched_at=datetime(2026, 5, 7, 11, 30, tzinfo=timezone.utc),
    )
    msg = crawler_sync.format_message(result, target_price=33000)
    assert "Elden Ring" in msg
    assert "33,000" in msg
    assert "66,000" in msg
    assert "Steam" in msg


def test_format_message_free():
    crawler_sync = SteamCrawler()
    result = PriceResult(
        site="steam", product_id="730", name="CS2",
        original_price=0, current_price=0,
        currency="KRW", url="https://store.steampowered.com/app/730",
    )
    msg = crawler_sync.format_message(result, target_price=0)
    assert "무료" in msg
