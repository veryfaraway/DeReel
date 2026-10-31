import re
from typing import Any

from loguru import logger

from dereel.core.base_crawler import BaseCrawler
from dereel.models.price_result import PriceResult

UTS_MOVIE_API_URL = "https://uts-api.itunes.apple.com/uts/v3/movies/{movie_id}"
UMC_ID_RE = re.compile(r"(umc\.cmc\.[a-z0-9]+)")

KR_STORE_PARAMS: dict[str, str] = {
    "utscf": "OjAAAAEAAAAAAAMAEAAAACMAKwAtADgA",
    "utsk": "0000000000000000::::::0000000000000000",
    "caller": "web",
    "sf": "143466",
    "v": "72",
    "pfm": "appletv",
    "locale": "ko-KR",
}


class AppleTvCrawler(BaseCrawler):
    """Apple TV 한국 스토어 영화 구매 가격 크롤러 (UTS v3 API)."""

    site_name = "apple_tv"

    async def fetch(self, url: str) -> list[PriceResult]:
        return []

    async def fetch_products(
        self,
        products: list[dict[str, Any]],
        currency: str = "KRW",
    ) -> list[PriceResult]:
        results: list[PriceResult] = []

        for product in products:
            raw_id = str(product["product_id"])
            name = product["name"]
            result = await self._fetch_one(raw_id, name, currency.upper())
            if result:
                results.append(result)

        return results

    async def _fetch_one(
        self,
        raw_id: str,
        name: str,
        currency: str,
    ) -> PriceResult | None:
        match = UMC_ID_RE.search(raw_id)
        movie_id = match.group(1) if match else raw_id

        try:
            resp = await self._client.get(
                UTS_MOVIE_API_URL.format(movie_id=movie_id),
                params=KR_STORE_PARAMS,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json().get("data") or {}
        except Exception as e:
            logger.error(f"[apple_tv] {name}({movie_id}) 조회 실패 — {e}")
            return None

        buy_price = self._extract_buy_price(data.get("playables") or {})
        if buy_price is None:
            logger.warning(f"[apple_tv] {name}({movie_id}) — 구매(buy) 가격 정보 없음")
            return None

        content = data.get("content") or {}
        store_url = str(content.get("url") or f"https://tv.apple.com/kr/movie/{movie_id}")

        logger.info(f"[apple_tv] {name}({movie_id}) — 현재 구매가: {buy_price:,.0f} {currency}")

        return PriceResult(
            site=self.site_name,
            product_id=raw_id,
            name=name,
            original_price=buy_price,
            current_price=buy_price,
            currency=currency,
            url=store_url,
        )

    @staticmethod
    def _extract_buy_price(playables: dict[str, Any]) -> float | None:
        """playables 내 itunesMediaApiData.offers에서 구매(kind='buy') 가격을 추출한다 (HD 우선)."""
        buy_offers: list[dict[str, Any]] = []
        for playable in playables.values():
            if not isinstance(playable, dict):
                continue
            media_data = playable.get("itunesMediaApiData") or {}
            for offer in media_data.get("offers") or []:
                if isinstance(offer, dict) and offer.get("kind") == "buy" and "price" in offer:
                    buy_offers.append(offer)

        if not buy_offers:
            return None

        hd_offer = next((o for o in buy_offers if o.get("variant") == "HD"), buy_offers[0])
        return float(hd_offer["price"])

    def format_message(self, result: PriceResult, target_price: float) -> str:
        return (
            f"🎬 [Apple TV 영화 가격 알림]\n\n"
            f"🍿 {result.name}\n"
            f"💸 현재 구매가: ₩{result.current_price:,.0f}\n"
            f"🎯 목표가:     ₩{target_price:,.0f}\n"
            f"🔗 {result.url}\n"
            f"🕐 {result.fetched_at.strftime('%Y-%m-%d %H:%M')} UTC"
        )
