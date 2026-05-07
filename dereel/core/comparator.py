from loguru import logger

from dereel.core.alert_history import AlertHistory
from dereel.core.notifier import Notifier
from dereel.core.storage import Storage
from dereel.models.price_result import PriceResult
from dereel.models.stock_result import StockResult


class Comparator:

    def __init__(self, storage: Storage, alert_history: AlertHistory, notifier: Notifier) -> None:
        self._storage = storage
        self._alert_history = alert_history
        self._notifier = notifier

    async def compare_stock(
        self,
        site_name: str,
        current: list[StockResult],
        dry_run: bool = False,
    ) -> None:
        """이전 재고 상태와 비교해 신규 입고 시 알림을 발송한다."""
        previous = self._storage.load_state(site_name)
        newly_stocked = []

        for result in current:
            was_in_stock = previous.get(result.product_id, False)
            if result.in_stock and not was_in_stock:
                newly_stocked.append(result)
                logger.info(f"[{site_name}] 신규 입고 감지 — {result.name}")

        for result in newly_stocked:
            alert_key = f"{site_name}:{result.product_id}:stock"
            if not self._alert_history.can_alert(alert_key):
                continue
            message = self._format_stock_message(result)
            await self._notifier.send(message, dry_run=dry_run)
            if not dry_run:
                self._alert_history.record(alert_key)

        # 현재 상태 저장
        new_state = {r.product_id: r.in_stock for r in current}
        self._storage.save_state(site_name, new_state)
        logger.info(f"[{site_name}] 상태 저장 완료 — {len(current)}건")

    def _format_stock_message(self, result: StockResult) -> str:
        price = f"₩{result.price:,}" if result.currency == "KRW" else f"{result.price:,} {result.currency}"
        return (
            f"🍎 [Apple 리퍼비시 입고]\n\n"
            f"📦 {result.name}\n"
            f"💰 가격: {price}\n"
            f"🔗 {result.url}"
        )

async def compare_price(
        self,
        site_name: str,
        results: list["PriceResult"],
        targets: list[dict],
        dry_run: bool = False,
    ) -> None:
        """현재 가격이 목표가 이하이거나 무료 전환 시 알림을 발송한다."""
        target_map = {str(t["app_id"]): t for t in targets}

        for result in results:
            target = target_map.get(result.product_id)
            if target is None:
                continue

            target_price = float(target.get("target_price", 0))

            if not result.should_notify(target_price):
                continue

            alert_key = f"{site_name}:{result.product_id}:price"
            if not self._alert_history.can_alert(alert_key):
                logger.info(f"[{site_name}] 중복 알림 스킵 — {result.name}")
                continue

            # SteamCrawler 인스턴스에서 메시지 포맷을 빌려오지 않고
            # Comparator가 직접 공통 포맷 사용
            message = self._format_price_message(result, target_price)
            await self._notifier.send(message, dry_run=dry_run)

            if not dry_run:
                self._alert_history.record(alert_key)   

def _format_price_message(self, result: "PriceResult", target_price: float) -> str:
        from dereel.models.price_result import PriceResult  # 순환참조 방지
        currency = result.currency
        symbol = "₩" if currency == "KRW" else ""
        fmt = lambda v: f"{symbol}{v:,.0f}{'' if symbol else ' ' + currency}"

        if result.is_free:
            price_line = "🎁 무료 전환!"
        else:
            price_line = (
                f"💸 현재가: {fmt(result.current_price)}\n"
                f"📌 원가: {fmt(result.original_price)}\n"
                f"🎯 목표가: {fmt(target_price)}"
            )

        site_emoji = {"steam": "🎮", "gog": "🟣", "epic": "🟦"}.get(result.site, "🛒")
        site_label = result.site.upper()

        return (
            f"{site_emoji} [{site_label} 가격 알림]\n\n"
            f"🕹 {result.name}\n"
            f"{price_line}\n"
            f"🔗 {result.url}\n"
            f"🕐 {result.fetched_at.strftime('%Y-%m-%d %H:%M')} UTC"
        )