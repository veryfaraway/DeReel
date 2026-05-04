from loguru import logger

from dereel.core.alert_history import AlertHistory
from dereel.core.notifier import Notifier
from dereel.core.storage import Storage
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
