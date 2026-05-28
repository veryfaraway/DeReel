# dereel/crawlers/epic.py
from typing import Any

from loguru import logger

from dereel.core.base_crawler import BaseCrawler
from dereel.models.price_result import PriceResult

FREE_GAMES_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"

CURRENCY_TO_COUNTRY: dict[str, str] = {
    "KRW": "KR", "USD": "US", "EUR": "DE", "JPY": "JP", "GBP": "GB",
}
COUNTRY_TO_LOCALE: dict[str, str] = {
    "KR": "ko", "US": "en-US", "DE": "de", "JP": "ja", "GB": "en",
}


class EpicCrawler(BaseCrawler):

    site_name = "epic"

    async def fetch(self, url: str) -> list[PriceResult]:
        return []

    async def fetch_products(
        self,
        products: list[dict[str, Any]],
        currency: str = "KRW",
    ) -> list[PriceResult]:
        """현재 무료 배포 중인 Epic 게임을 조회한다.
        products가 비어있으면 전체 무료 게임, slug 기재 시 watchlist 필터링."""
        country = CURRENCY_TO_COUNTRY.get(currency.upper(), "US")
        locale = COUNTRY_TO_LOCALE.get(country, "en-US")

        try:
            resp = await self._client.get(
                FREE_GAMES_URL,
                params={"locale": locale, "country": country, "allowCountries": country},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"[epic] 무료 게임 프로모션 조회 실패 — {e}")
            return []

        elements: list[dict[str, Any]] = (
            data.get("data", {})
                .get("Catalog", {})
                .get("searchStore", {})
                .get("elements", [])
        )
        watchlist = {str(p["slug"]) for p in products if "slug" in p}

        results: list[PriceResult] = []
        for item in elements:
            if not self._is_currently_free(item):
                continue

            slug = self._extract_slug(item)
            if watchlist and slug not in watchlist:
                continue

            name = item.get("title", "Unknown")
            original_price = (
                item.get("price", {}).get("totalPrice", {}).get("originalPrice", 0)
            ) / 100

            logger.info(f"[epic] 무료 게임 감지 — {name} (원가: {original_price:,.0f} {currency})")
            results.append(PriceResult(
                site="epic",
                product_id=slug,
                name=name,
                original_price=original_price,
                current_price=0.0,
                currency=currency,
                url=f"https://store.epicgames.com/ko/p/{slug}",
            ))

        return results

    @staticmethod
    def _is_currently_free(item: dict[str, Any]) -> bool:
        for offer_group in item.get("promotions", {}).get("promotionalOffers", []):
            for offer in offer_group.get("promotionalOffers", []):
                setting = offer.get("discountSetting", {})
                if setting.get("discountType") == "PERCENTAGE" and setting.get("discountPercentage") == 0:
                    return True
        return False

    @staticmethod
    def _extract_slug(item: dict[str, Any]) -> str:
        raw = item.get("productSlug") or item.get("urlSlug") or item.get("id", "")
        return str(raw).split("/")[0]

    def format_message(self, result: PriceResult, target_price: float) -> str:
        symbol = "₩" if result.currency == "KRW" else ""
        suffix = "" if symbol else f" {result.currency}"
        return (
            f"🎮 [Epic 무료 게임 알림]\n\n"
            f"🎁 {result.name}\n"
            f"💸 원가: {symbol}{result.original_price:,.0f}{suffix} → 지금 무료!\n"
            f"🔗 {result.url}\n"
            f"🕐 {result.fetched_at.strftime('%Y-%m-%d %H:%M')} UTC"
        )
