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


# ── Package ID 및 Fallback 테스트 ────────────────────────────────────────────────
MOCK_API_RESPONSE_PACKAGE = {
    "6588": {
        "success": True,
        "data": {
            "price_overview": {
                "currency": "KRW",
                "initial": 2000000,
                "final": 1000000,
                "discount_percent": 50,
            }
        },
    }
}


@pytest.mark.asyncio
async def test_fetch_package_id_directly(crawler):
    """package_id가 지정된 경우 처음부터 패키지 API를 바로 찌른다."""
    products = [{"package_id": "6588", "name": "Monkey Island Collection", "target_price": 20000}]

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = MOCK_API_RESPONSE_PACKAGE

    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products(products, currency="KRW")

    assert len(results) == 1
    assert results[0].product_id == "6588"
    assert results[0].original_price == 20000.0
    assert results[0].current_price == 10000.0
    assert results[0].url == "https://store.steampowered.com/sub/6588"


@pytest.mark.asyncio
async def test_fetch_app_id_fallback_to_package(crawler):
    """app_id로 기입했으나 app API가 실패할 때 package API로 우회 작동(Fallback)한다."""
    products = [{"app_id": "6588", "name": "Monkey Island Collection", "target_price": 20000}]

    # 1차 appdetails 실패 응답
    mock_resp_fail = MagicMock()
    mock_resp_fail.raise_for_status = MagicMock()
    mock_resp_fail.json.return_value = {"6588": {"success": False}}

    # 2차 packagedetails 성공 응답
    mock_resp_success = MagicMock()
    mock_resp_success.raise_for_status = MagicMock()
    mock_resp_success.json.return_value = MOCK_API_RESPONSE_PACKAGE

    # 1차 호출 시 fail, 2차 호출 시 success 반환하도록 세팅
    crawler._client.get = AsyncMock(side_effect=[mock_resp_fail, mock_resp_success])

    results = await crawler.fetch_products(products, currency="KRW")

    assert len(results) == 1
    assert results[0].product_id == "6588"
    assert results[0].original_price == 20000.0
    assert results[0].current_price == 10000.0
    assert results[0].url == "https://store.steampowered.com/sub/6588"

