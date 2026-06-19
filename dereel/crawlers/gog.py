from typing import Any

from loguru import logger

from dereel.core.base_crawler import BaseCrawler
from dereel.models.price_result import PriceResult

PRICES_URL  = "https://api.gog.com/products/{product_id}/prices"
PRODUCT_URL = "https://api.gog.com/products/{product_id}"

CURRENCY_TO_CC: dict[str, str] = {
    "USD": "US", "EUR": "DE", "GBP": "GB",
    "JPY": "JP", "KRW": "KR",
}


class GogCrawler(BaseCrawler):

    site_name = "gog"

    async def fetch(self, url: str) -> list[PriceResult]:
        return []

    async def fetch_products(
        self,
        products: list[dict[str, Any]],
        currency: str = "USD",
    ) -> list[PriceResult]:
        cc = CURRENCY_TO_CC.get(currency.upper(), "US")
        results: list[PriceResult] = []

        for product in products:
            product_id = str(product["product_id"])
            name = product["name"]
            result = await self._fetch_one(product_id, name, currency, cc)
            if result:
                results.append(result)

        return results

    async def _fetch_one(
        self,
        product_id: str,
        name: str,
        currency: str,
        cc: str,
    ) -> PriceResult | None:
        try:
            resp = await self._client.get(
                PRICES_URL.format(product_id=product_id),
                params={"countryCode": cc},
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"[gog] {name}({product_id}) 가격 요청 실패 — {e}")
            return None

        prices = data.get("_embedded", {}).get("prices", [])
        target_currency = currency.upper()

        # 요청한 통화 매칭
        price_entry = next(
            (p for p in prices if p["currency"]["code"] == target_currency),
            prices[0] if prices else None,
        )

        if price_entry is None:
            logger.warning(f"[gog] {name}({product_id}) — 가격 정보 없음")
            return None

        # "999 USD" → 9.99
        original = self._parse_price(price_entry["basePrice"])
        current  = self._parse_price(price_entry["finalPrice"])

        slug = product_id
        try:
            prod_resp = await self._client.get(
                PRODUCT_URL.format(product_id=product_id),
                headers={"Accept": "application/json"}
            )
            if prod_resp.status_code == 200:
                slug = prod_resp.json().get("slug", product_id)
        except Exception as e:
            logger.warning(f"[gog] {name}({product_id}) slug 정보 조회 실패 — {e}")

        store_url = f"https://www.gog.com/en/game/{slug}"

        # 무료 게임
        if current == 0:
            logger.info(f"[gog] {name}({product_id}) — 무료 게임 감지")
            return PriceResult(
                site="gog", product_id=product_id, name=name,
                original_price=0.0, current_price=0.0,
                currency=target_currency, url=store_url,
            )

        logger.info(
            f"[gog] {name}({product_id}) — "
            f"원가: {original} {currency} / 현재가: {current} {currency}"
        )

        return PriceResult(
            site="gog", product_id=product_id, name=name,
            original_price=original, current_price=current,
            currency=target_currency, url=store_url,
        )

    @staticmethod
    def _parse_price(price_str: str) -> float:
        """'999 USD' → 9.99, '0 USD' → 0.0"""
        amount_cents = int(price_str.split()[0])
        return round(amount_cents / 100, 2)

    def format_message(self, result: PriceResult, target_price: float) -> str:
        symbol = "$" if result.currency == "USD" else ""
        suffix = "" if symbol else f" {result.currency}"
        discount_pct = (
            round((1 - result.current_price / result.original_price) * 100)
            if result.original_price > 0 else 0
        )

        if result.is_free:
            price_line = "🎁 무료 전환!"
        else:
            price_line = (
                f"💸 현재가: {symbol}{result.current_price:.2f}{suffix}"
                + (f" ({discount_pct}% 할인)" if discount_pct > 0 else "") + "\n"
                f"📌 원가:   {symbol}{result.original_price:.2f}{suffix}\n"
                f"🎯 목표가: {symbol}{target_price:.2f}{suffix}"
            )

        return (
            f"🎮 [GOG 가격 알림]\n\n"
            f"🕹 {result.name}\n"
            f"{price_line}\n"
            f"🔗 {result.url}\n"
            f"🕐 {result.fetched_at.strftime('%Y-%m-%d %H:%M')} UTC"
        )
