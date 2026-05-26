# dereel/crawlers/steam.py
from loguru import logger
import httpx

from dereel.core.base_crawler import BaseCrawler
from dereel.models.price_result import PriceResult

STEAM_API_URL = "https://store.steampowered.com/api/appdetails"
STEAM_PACKAGE_API_URL = "https://store.steampowered.com/api/packagedetails"


CURRENCY_TO_CC: dict[str, str] = {
    "KRW": "kr",
    "USD": "us",
    "EUR": "de",
    "JPY": "jp",
    "GBP": "gb",
}


class SteamCrawler(BaseCrawler):

    async def fetch(self, url: str) -> list[PriceResult]:
        """추상 메서드 구현체 (실제 조회는 fetch_products를 사용)."""
        return []

    async def fetch_products(
        self,
        products: list[dict],
        currency: str = "KRW",
    ) -> list[PriceResult]:
        """products 리스트를 받아 Steam API로 가격을 조회한다."""
        cc = CURRENCY_TO_CC.get(currency.upper(), "us")
        results: list[PriceResult] = []

        for product in products:
            app_id = product.get("app_id")
            package_id = product.get("package_id")
            name = product["name"]

            # 1. package_id가 명확히 지정된 경우 바로 패키지 API 조회 (최적화)
            if package_id:
                result = await self._fetch_package(str(package_id), name, currency, cc)
                if result:
                    results.append(result)
                continue

            # 2. app_id로 지정된 경우
            if app_id:
                app_id_str = str(app_id)
                # 단일 앱 조회 시도
                result = await self._fetch_app(app_id_str, name, currency, cc)

                # 단일 앱 조회 실패 시, 사용자가 패키지 ID를 app_id로 적었을 가능성에 대비한 Fallback 구동
                if result is None:
                    logger.info(f"[steam] {name}({app_id_str}) App 조회 실패 — Package Fallback 실행")
                    result = await self._fetch_package(app_id_str, name, currency, cc)

                if result:
                    results.append(result)

        return results

    async def _fetch_app(
        self,
        app_id: str,
        name: str,
        currency: str,
        cc: str,
    ) -> PriceResult | None:
        """단일 앱(App ID) 상세 정보를 조회한다."""
        try:
            resp = await self._client.get(
                STEAM_API_URL,
                params={"appids": app_id, "cc": cc, "filters": "price_overview"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"[steam] {name}({app_id}) App 요청 실패 — {e}")
            return None

        entry = data.get(app_id, {})
        if not entry.get("success"):
            logger.debug(f"[steam] {name}({app_id}) App API success=false — Package 감지 필요")
            return None

        price_data = entry.get("data", {}).get("price_overview")
        return self._build_price_result(app_id, name, price_data, currency, is_package=False)

    async def _fetch_package(
        self,
        package_id: str,
        name: str,
        currency: str,
        cc: str,
    ) -> PriceResult | None:
        """패키지(Sub ID) 상세 정보를 조회한다."""
        try:
            resp = await self._client.get(
                STEAM_PACKAGE_API_URL,
                params={"packageids": package_id, "cc": cc},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"[steam] {name}({package_id}) Package 요청 실패 — {e}")
            return None

        entry = data.get(package_id, {})
        if not entry.get("success"):
            logger.warning(f"[steam] {name}({package_id}) Package API success=false")
            return None

        price_data = entry.get("data", {}).get("price_overview")
        return self._build_price_result(package_id, name, price_data, currency, is_package=True)

    def _build_price_result(
        self,
        product_id: str,
        name: str,
        price_data: dict | None,
        currency: str,
        is_package: bool = False,
    ) -> PriceResult:
        store_url = (
            f"https://store.steampowered.com/sub/{product_id}"
            if is_package
            else f"https://store.steampowered.com/app/{product_id}"
        )

        # 무료 게임/패키지 처리
        if price_data is None:
            logger.info(f"[steam] {name}({product_id}) — 무료 {'패키지' if is_package else '게임'} 감지")
            return PriceResult(
                site="steam",
                product_id=product_id,
                name=name,
                original_price=0.0,
                current_price=0.0,
                currency=currency,
                url=store_url,
            )

        original = price_data["initial"] / 100
        current = price_data["final"] / 100

        logger.info(
            f"[steam] {name}({product_id}) — "
            f"원가: {original:,.0f} {currency} / "
            f"현재가: {current:,.0f} {currency} "
            f"({price_data['discount_percent']}% 할인)"
        )

        return PriceResult(
            site="steam",
            product_id=product_id,
            name=name,
            original_price=original,
            current_price=current,
            currency=currency,
            url=store_url,
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

