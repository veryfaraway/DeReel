# dereel/crawlers/steam.py
import json
from typing import Any

from bs4 import BeautifulSoup
from loguru import logger

from dereel.core.base_crawler import BaseCrawler
from dereel.models.price_result import PriceResult

STEAM_API_URL = "https://store.steampowered.com/api/appdetails"
STEAM_PACKAGE_API_URL = "https://store.steampowered.com/api/packagedetails"
STEAM_BUNDLE_STORE_URL = "https://store.steampowered.com/bundle"


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
        products: list[dict[str, Any]],
        currency: str = "KRW",
    ) -> list[PriceResult]:
        """products 리스트를 받아 Steam API로 가격을 조회한다."""
        cc = CURRENCY_TO_CC.get(currency.upper(), "us")
        results: list[PriceResult] = []

        for product in products:
            app_id = product.get("app_id")
            package_id = product.get("package_id")
            bundle_id = product.get("bundle_id")
            name = product["name"]

            # 1. bundle_id가 명확히 지정된 경우 바로 번들 API 조회
            if bundle_id:
                result = await self._fetch_bundle(str(bundle_id), name, currency, cc)
                if result:
                    results.append(result)
                continue

            # 2. package_id가 명확히 지정된 경우 바로 패키지 API 조회 (최적화)
            if package_id:
                result = await self._fetch_package(str(package_id), name, currency, cc)
                if result:
                    results.append(result)
                continue

            # 3. app_id로 지정된 경우
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
        return self._build_price_result(app_id, name, price_data, currency, product_type="app")

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

        price_data = entry.get("data", {}).get("price")
        return self._build_price_result(package_id, name, price_data, currency, product_type="package")

    async def _fetch_bundle(
        self,
        bundle_id: str,
        name: str,
        currency: str,
        cc: str,
    ) -> PriceResult | None:
        """번들(Bundle ID) 스토어 페이지를 스크래핑하여 가격을 조회한다.
        /api/bundledetails는 403을 반환하므로 HTML 파싱 방식을 사용한다."""
        url = f"{STEAM_BUNDLE_STORE_URL}/{bundle_id}/"
        try:
            resp = await self._client.get(url, params={"cc": cc, "l": "english"})
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            logger.error(f"[steam] {name}({bundle_id}) Bundle 페이지 요청 실패 — {e}")
            return None

        soup = BeautifulSoup(html, "html.parser")
        bundle_div = soup.find("div", {"data-ds-bundleid": bundle_id})
        if bundle_div is None:
            logger.warning(f"[steam] {name}({bundle_id}) Bundle 데이터 div 미발견")
            return None

        try:
            items = json.loads(str(bundle_div.get("data-ds-bundle-data", "{}"))).get("m_rgItems", [])
            original_cents = sum(item.get("m_nBasePriceInCents", 0) for item in items)
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"[steam] {name}({bundle_id}) Bundle 데이터 파싱 실패 — {e}")
            return None

        price_div = bundle_div.find(attrs={"data-price-final": True})
        if price_div is None:
            logger.warning(f"[steam] {name}({bundle_id}) data-price-final 미발견")
            return None

        final_cents = int(str(price_div["data-price-final"]))
        discount_pct = int(str(price_div.get("data-bundlediscount", "0")))

        price_data: dict[str, Any] | None = (
            None if original_cents == 0 and final_cents == 0
            else {"initial": original_cents, "final": final_cents, "discount_percent": discount_pct}
        )
        return self._build_price_result(bundle_id, name, price_data, currency, product_type="bundle")

    def _build_price_result(
        self,
        product_id: str,
        name: str,
        price_data: dict[str, Any] | None,
        currency: str,
        product_type: str = "app",
    ) -> PriceResult:
        if product_type == "package":
            store_url = f"https://store.steampowered.com/sub/{product_id}"
        elif product_type == "bundle":
            store_url = f"https://store.steampowered.com/bundle/{product_id}"
        else:
            store_url = f"https://store.steampowered.com/app/{product_id}"

        type_label = {"package": "패키지", "bundle": "번들"}.get(product_type, "게임")

        # 무료 게임/패키지/번들 처리
        if price_data is None:
            logger.info(f"[steam] {name}({product_id}) — 무료 {type_label} 감지")
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

