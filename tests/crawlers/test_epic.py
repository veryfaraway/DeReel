# tests/crawlers/test_epic.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from dereel.crawlers.epic import EpicCrawler
from dereel.models.price_result import PriceResult


def _make_element(title: str, slug: str, original: int, free_promo: bool) -> dict:
    return {
        "title": title,
        "id": slug,
        "productSlug": slug,
        "price": {
            "totalPrice": {
                "originalPrice": original,
                "discountPrice": 0 if free_promo else original,
            }
        },
        "promotions": {
            "promotionalOffers": (
                [{"promotionalOffers": [{"discountSetting": {"discountType": "PERCENTAGE", "discountPercentage": 0}}]}]
                if free_promo else []
            )
        },
    }


MOCK_RESPONSE = {
    "data": {"Catalog": {"searchStore": {"elements": [
        _make_element("Transistor", "transistor", 1490000, free_promo=True),
        _make_element("Paid Game", "paid-game", 5990000, free_promo=False),
    ]}}}
}


@pytest.fixture
async def crawler():
    async with EpicCrawler() as c:
        yield c


@pytest.mark.asyncio
async def test_fetch_detects_free_game(crawler):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = MOCK_RESPONSE
    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products([], currency="KRW")

    assert len(results) == 1
    r = results[0]
    assert isinstance(r, PriceResult)
    assert r.site == "epic"
    assert r.product_id == "transistor"
    assert r.original_price == 14900.0
    assert r.current_price == 0.0
    assert r.is_free is True


@pytest.mark.asyncio
async def test_fetch_watchlist_match(crawler):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = MOCK_RESPONSE
    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products(
        [{"slug": "transistor", "name": "Transistor", "target_price": 0}],
        currency="KRW",
    )
    assert len(results) == 1
    assert results[0].product_id == "transistor"


@pytest.mark.asyncio
async def test_fetch_watchlist_no_match(crawler):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = MOCK_RESPONSE
    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products(
        [{"slug": "not-in-list", "name": "X", "target_price": 0}],
        currency="KRW",
    )
    assert results == []


@pytest.mark.asyncio
async def test_fetch_returns_empty_on_api_failure(crawler):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("timeout")
    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products([], currency="KRW")
    assert results == []


@pytest.mark.asyncio
@pytest.mark.parametrize("null_response", [
    {"data": None},
    {"data": {"Catalog": None}},
    {"data": {"Catalog": {"searchStore": None}}},
    {"data": {"Catalog": {"searchStore": {"elements": None}}}},
])
async def test_fetch_returns_empty_on_null_response(crawler, null_response):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = null_response
    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products([], currency="KRW")
    assert results == []


def test_format_message():
    from datetime import datetime, timezone
    result = PriceResult(
        site="epic", product_id="transistor", name="Transistor",
        original_price=14900, current_price=0, currency="KRW",
        url="https://store.epicgames.com/ko/p/transistor",
        fetched_at=datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc),
    )
    msg = EpicCrawler().format_message(result, target_price=0)
    assert "Transistor" in msg
    assert "14,900" in msg
    assert "무료" in msg
    assert "Epic" in msg
