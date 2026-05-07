# dereel/crawlers/steam.py
from loguru import logger
import httpx

from dereel.core.base_crawler import BaseCrawler
from dereel.models.price_result import PriceResult

STEAM_API_URL = "https://store.steampowered.com/api/appdetails"

CURRENCY_TO_CC: dict[str, str] = {
    "KRW": "kr",
    "USD": "us",
    "EUR": "de",
    "JPY": "jp",
    "GBP": "gb",
}


class SteamCrawler(BaseCrawler):

    site_name = "steam"   # 클래스 변수 (BaseCrawler 패턴과 동일)

    async def fetch(self, url: str) -> list[PriceResult]:
        """targets.yaml의 products 리스트를 순회하며 가격을 조회한다."""
        products = url  # run.py에서 target 전체를 넘기는 방식으로 사용
        # ※ run.py와 연동 방식은 아래 run_patch 참고
        return []  # 실제 구현은 fetch_products()를 사용

    async def fetch_products(
        self,
        products: list[dict],
        currency: str = "KRW",
    ) -> list[PriceResult]:
        """products 리스트를 받아 Steam API로 가격을 조회한다."""
        cc = CURRENCY_TO_CC.get(currency.upper(), "us")
        results: list[PriceResult] = []

        for product in products:
            app_id = str(product["app_id"])
            name = product["name"]
            result = await self._fetch_one(app_id, name, currency, cc)
            if result:
                results.append(result)

        return results

    async def _fetch_one(
        self,
        app_id: str,
        name: str,
        currency: str,
        cc: str,
    ) -> PriceResult | None:
        try:
            resp = await self._client.get(
                STEAM_API_URL,
                params={"appids": app_id, "cc": cc, "filters": "price_overview"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"[steam] {name}({app_id}) 요청 실패 — {e}")
            return None

        entry = data.get(app_id, {})
        if not entry.get("success"):
            logger.warning(f"[steam] {name}({app_id}) — Steam API success=false")
            return None

        price_data = entry.get("data", {}).get("price_overview")

        # 무료 게임 (price_overview 없음)
        if price_data is None:
            logger.info(f"[steam] {name}({app_id}) — 무료 게임 감지")
            return PriceResult(
                site="steam",
                product_id=app_id,
                name=name,
                original_price=0,
                current_price=0,
                currency=currency,
                url=f"https://store.steampowered.com/app/{app_id}",
            )

        original = price_data["initial"] / 100
        current = price_data["final"] / 100

        logger.info(
            f"[steam] {name}({app_id}) — "
            f"원가: {original:,.0f} {currency} / "
            f"현재가: {current:,.0f} {currency} "
            f"({price_data['discount_percent']}% 할인)"
        )

        return PriceResult(
            site="steam",
            product_id=app_id,
            name=name,
            original_price=original,
            current_price=current,
            currency=currency,
            url=f"https://store.steampowered.com/app/{app_id}",
        )

    def format_message(self, result: PriceResult, target_price: float) -> str:
        symbol = "₩" if result.currency == "KRW" else ""
        suffix = "" if symbol else f" {result.currency}"

        if result.is_free:
            price_line = "🎁 무료 전환!"
        else:
            price_line = (
                f"💸 현재가: {symbol}{result.current_price:,.0f}{suffix}\n"
                f"📌 원가:   {symbol}{result.original_price:,.0f}{suffix}\n"
                f"🎯 목표가: {symbol}{target_price:,.0f}{suffix}"
            )

        return (
            f"🎮 [Steam 가격 알림]\n\n"
            f"🕹 {result.name}\n"
            f"{price_line}\n"
            f"🔗 {result.url}\n"
            f"🕐 {result.fetched_at.strftime('%Y-%m-%d %H:%M')} UTC"
        )
