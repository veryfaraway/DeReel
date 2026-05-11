from loguru import logger

from dereel.core.base_crawler import BaseCrawler
from dereel.models.price_result import PriceResult

CATALOG_URL = "https://catalog.gog.com/v1/catalog"

CURRENCY_TO_CC: dict[str, str] = {
    "USD": "US",
    "EUR": "DE",
    "GBP": "GB",
    "JPY": "JP",
    "KRW": "KR",
}


class GogCrawler(BaseCrawler):

    site_name = "gog"

    async def fetch(self, url: str) -> list[PriceResult]:
        """BaseCrawler.fetch() 시그니처 준수용 — 실제 진입점은 fetch_products()."""
        return []

    async def fetch_products(
        self,
        products: list[dict],
        currency: str = "USD",
    ) -> list[PriceResult]:
        cc = CURRENCY_TO_CC.get(currency.upper(), "US")
        results: list[PriceResult] = []

        for product in products:
            slug = product["slug"]
            name = product["name"]
            result = await self._fetch_one(slug, name, currency, cc)
            if result:
                results.append(result)

        return results

    async def _fetch_one(
        self,
        slug: str,
        name: str,
        currency: str,
        cc: str,
    ) -> PriceResult | None:
        try:
            resp = await self._client.get(
                CATALOG_URL,
                params={
                    "slugs": slug,
                    "limit": 1,
                    "productType": "in:game",
                    "countryCode": cc,
                    "currencyCode": currency.upper(),
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"[gog] {name}({slug}) 요청 실패 — {e}")
            return None

        products = data.get("products", [])

        # slug 정확히 일치하는 항목 탐색
        matched = next((p for p in products if p.get("slug") == slug), None)

        if matched is None:
            logger.warning(f"[gog] {name}({slug}) — 일치하는 상품 없음")
            return None

        price_data = matched.get("price")
        product_id = str(matched["id"])
        store_url = f"https://www.gog.com/game/{slug}"

        # 무료 게임 (price 없음)
        if price_data is None:
            logger.info(f"[gog] {name}({slug}) — 무료 게임 감지")
            return PriceResult(
                site="gog",
                product_id=product_id,
                name=name,
                original_price=0.0,
                current_price=0.0,
                currency=currency.upper(),
                url=store_url,
            )

        original = float(price_data["baseMoney"]["amount"])
        current = float(price_data["finalMoney"]["amount"])

        logger.info(
            f"[gog] {name}({slug}) — "
            f"원가: {original} {currency} / 현재가: {current} {currency}"
        )

        return PriceResult(
            site="gog",
            product_id=product_id,
            name=name,
            original_price=original,
            current_price=current,
            currency=currency.upper(),
            url=store_url,
        )

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