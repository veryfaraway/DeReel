from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from dereel.crawlers.apple_tv import AppleTvCrawler
from dereel.models.price_result import PriceResult


def _make_uts_response(
    buy_hd_price: int | None = 5000,
    buy_sd_price: int | None = 5000,
    rent_hd_price: int | None = 3000,
    url: str = "https://tv.apple.com/kr/movie/stardust/umc.cmc.535568gf8g1wriibl03pf1vqo",
) -> dict:
    offers = []
    if buy_sd_price is not None:
        offers.append({"kind": "buy", "price": buy_sd_price, "variant": "SD"})
    if buy_hd_price is not None:
        offers.append({"kind": "buy", "price": buy_hd_price, "variant": "HD"})
    if rent_hd_price is not None:
        offers.append({"kind": "rent", "price": rent_hd_price, "variant": "HD"})

    return {
        "data": {
            "content": {
                "id": "umc.cmc.535568gf8g1wriibl03pf1vqo",
                "title": "스타더스트",
                "url": url,
            },
            "playables": {
                "tvs.sbd.4000:SUB": {
                    "serviceName": "Apple TV+",
                    "itunesMediaApiData": None,
                },
                "tvs.sbd.9001:273701540": {
                    "title": "스타더스트",
                    "itunesMediaApiData": {
                        "offers": offers,
                    },
                },
            },
        }
    }


MOCK_PRODUCTS = [
    {
        "product_id": "umc.cmc.535568gf8g1wriibl03pf1vqo",
        "name": "스타더스트 (Stardust, 2007)",
        "target_price": 3500,
    }
]


@pytest.fixture
async def crawler():
    async with AppleTvCrawler() as c:
        yield c


@pytest.mark.asyncio
async def test_fetch_products_returns_buy_price(crawler):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = _make_uts_response(buy_hd_price=5000, buy_sd_price=4000, rent_hd_price=3000)

    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products(MOCK_PRODUCTS, currency="KRW")

    assert len(results) == 1
    assert isinstance(results[0], PriceResult)
    assert results[0].site == "apple_tv"
    assert results[0].product_id == "umc.cmc.535568gf8g1wriibl03pf1vqo"
    assert results[0].current_price == 5000.0
    assert results[0].original_price == 5000.0
    assert results[0].currency == "KRW"


@pytest.mark.asyncio
async def test_fetch_products_extracts_umc_id_from_full_url(crawler):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = _make_uts_response(buy_hd_price=3500)

    crawler._client.get = AsyncMock(return_value=mock_resp)

    full_url_product = [
        {
            "product_id": "https://tv.apple.com/kr/movie/stardust/umc.cmc.535568gf8g1wriibl03pf1vqo",
            "name": "스타더스트",
            "target_price": 3500,
        }
    ]
    results = await crawler.fetch_products(full_url_product, currency="KRW")

    assert len(results) == 1
    assert results[0].current_price == 3500.0
    called_url = crawler._client.get.call_args[0][0]
    assert called_url.endswith("/umc.cmc.535568gf8g1wriibl03pf1vqo")


@pytest.mark.asyncio
async def test_fetch_products_skips_when_only_rent_available(crawler):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = _make_uts_response(buy_hd_price=None, buy_sd_price=None, rent_hd_price=3000)

    crawler._client.get = AsyncMock(return_value=mock_resp)

    results = await crawler.fetch_products(MOCK_PRODUCTS, currency="KRW")
    assert results == []


@pytest.mark.asyncio
async def test_fetch_products_returns_empty_on_http_error(crawler):
    crawler._client.get = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock(status_code=500)
        )
    )

    results = await crawler.fetch_products(MOCK_PRODUCTS, currency="KRW")
    assert results == []


def test_format_message():
    crawler = AppleTvCrawler()
    result = PriceResult(
        site="apple_tv",
        product_id="umc.cmc.535568gf8g1wriibl03pf1vqo",
        name="스타더스트 (Stardust, 2007)",
        original_price=3500,
        current_price=3500,
        currency="KRW",
        url="https://tv.apple.com/kr/movie/umc.cmc.535568gf8g1wriibl03pf1vqo",
        fetched_at=datetime(2026, 11, 1, 0, 0, tzinfo=UTC),
    )
    msg = crawler.format_message(result, target_price=3500)

    assert "Apple TV" in msg
    assert "스타더스트" in msg
    assert "₩3,500" in msg


def test_site_name_class_variable():
    assert AppleTvCrawler.site_name == "apple_tv"
