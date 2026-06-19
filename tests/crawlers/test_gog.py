import pytest
from unittest.mock import AsyncMock, MagicMock
from dereel.crawlers.gog import GogCrawler
from dereel.models.price_result import PriceResult

# ── Mock API 응답 ─────────────────────────────────────────────────────────────
def _make_prices_response(base_cents: int, final_cents: int, currency: str = "USD") -> dict:
    return {
        "_embedded": {
            "prices": [
                {
                    "currency": {"code": currency},
                    "basePrice": f"{base_cents} {currency}",
                    "finalPrice": f"{final_cents} {currency}"
                }
            ]
        }
    }

MOCK_PRODUCTS = [
    {"product_id": "1207664663", "slug": "the_witcher_3_wild_hunt", "name": "The Witcher 3", "target_price": 9.99},
]

MOCK_FREE_PRODUCTS = [
    {"product_id": "1207664997", "slug": "gwent_the_witcher_card_game", "name": "Gwent", "target_price": 0},
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
    mock_resp.json.return_value = _make_prices_response(3999, 999, "USD")

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
    mock_resp.json.return_value = _make_prices_response(0, 0, "USD")

    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products(MOCK_FREE_PRODUCTS, currency="USD")

    assert len(results) == 1
    assert results[0].is_free
    assert results[0].current_price == 0.0


@pytest.mark.asyncio
async def test_fetch_returns_empty_when_no_prices_embedded(crawler):
    """GOG API 응답에 가격 정보가 없는 경우 빈 리스트를 반환한다."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"_embedded": {"prices": []}}

    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products(MOCK_PRODUCTS, currency="USD")

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


@pytest.mark.asyncio
async def test_fetch_slug_from_product_url(crawler):
    mock_prices_resp = MagicMock()
    mock_prices_resp.raise_for_status = MagicMock()
    mock_prices_resp.json.return_value = _make_prices_response(3999, 999, "USD")

    mock_product_resp = MagicMock()
    mock_product_resp.status_code = 200
    mock_product_resp.json.return_value = {"slug": "real_slug_from_api"}

    async def mock_get(url, **kwargs):
        if "prices" in url:
            return mock_prices_resp
        return mock_product_resp

    crawler._client.get = AsyncMock(side_effect=mock_get)

    results = await crawler.fetch_products(MOCK_PRODUCTS, currency="USD")
    
    assert len(results) == 1
    assert results[0].url == "https://www.gog.com/en/game/real_slug_from_api"


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