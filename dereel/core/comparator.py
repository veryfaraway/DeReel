from loguru import logger

from dereel.core.alert_history import AlertHistory
from dereel.core.notifier import Notifier
from dereel.core.base_storage import Storage
from dereel.models.price_result import PriceResult
from dereel.models.stock_result import StockResult


class Comparator:

    def __init__(self, storage: Storage, alert_history: AlertHistory, notifier: Notifier) -> None:
        self._storage = storage
        self._alert_history = alert_history
        self._notifier = notifier

    # ── 재고 비교 (apple_refurb) ───────────────────────────────────────────
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

        new_state = {r.product_id: r.in_stock for r in current}
        self._storage.save_state(site_name, new_state)
        logger.info(f"[{site_name}] 상태 저장 완료 — {len(current)}건")

    # ── 가격 비교 (steam / gog / epic …) ──────────────────────────────────
    async def compare_price(
        self,
        site_name: str,
        current: list[PriceResult],
        products_config: list[dict],
        dry_run: bool = False,
    ) -> None:
        """이전 가격과 비교해 목표가 도달 또는 무료 전환 시 알림을 발송한다."""
        # product_id → target_price 맵 생성
        target_map: dict[str, float] = {}
        for p in products_config:
            product_id = str(p.get("app_id") or p.get("package_id") or p.get("product_id") or p.get("slug", ""))
            target_map[product_id] = float(p.get("target_price", 0))

        previous = self._storage.load_state(site_name)

        for result in current:
            prev_price: float = previous.get(result.product_id, float("inf"))
            target_price = target_map.get(result.product_id, 0.0)

            should_notify = (
                result.is_free                                  # 무료 전환
                or (
                    result.current_price <= target_price        # 목표가 도달
                    and prev_price > target_price               # 이전엔 목표가 초과였음
                )
            )

            if not should_notify:
                logger.debug(
                    f"[{site_name}] {result.name} — "
                    f"현재가 {result.current_price} / 목표가 {target_price} / 이전가 {prev_price} (알림 없음)"
                )
                continue

            logger.info(f"[{site_name}] 알림 조건 충족 — {result.name} ({result.current_price})")

            alert_type = "free" if result.is_free else "price"
            alert_key = f"{site_name}:{result.product_id}:{alert_type}"

            if not self._alert_history.can_alert(alert_key, current_price=result.current_price):
                logger.debug(f"[{site_name}] 쿨다운 중 — {alert_key}")
                continue

            message = self._format_price_message(result, target_price)
            await self._notifier.send(message, dry_run=dry_run)

            if not dry_run:
                self._alert_history.record(alert_key, current_price=result.current_price)

        # 현재 가격 상태 저장
        new_state = {r.product_id: r.current_price for r in current}
        self._storage.save_state(site_name, new_state)
        logger.info(f"[{site_name}] 가격 상태 저장 완료 — {len(current)}건")

    # ── 메시지 포맷 ────────────────────────────────────────────────────────
    def _format_stock_message(self, result: StockResult) -> str:
        price = f"₩{result.price:,}" if result.currency == "KRW" else f"{result.price:,} {result.currency}"
        return (
            f"🍎 [Apple 리퍼비시 입고]\n\n"
            f"📦 {result.name}\n"
            f"💰 가격: {price}\n"
            f"🔗 {result.url}"
        )

    def _format_price_message(self, result: PriceResult, target_price: float) -> str:
        symbol = "₩" if result.currency == "KRW" else ("$" if result.currency == "USD" else "")
        suffix = "" if symbol else f" {result.currency}"

        if result.is_free:
            price_line = "🎁 무료 전환!"
        else:
            discount_pct = (
                round((1 - result.current_price / result.original_price) * 100)
                if result.original_price > 0 else 0
            )
            price_line = (
                f"💸 현재가: {symbol}{result.current_price:,.2f}{suffix}"
                + (f" ({discount_pct}% 할인)" if discount_pct > 0 else "") + "\n"
                f"📌 원가:   {symbol}{result.original_price:,.2f}{suffix}\n"
                f"🎯 목표가: {symbol}{target_price:,.2f}{suffix}"
            )

        site_label = {"steam": "Steam", "gog": "GOG", "epic": "Epic Games"}.get(result.site, result.site)
        return (
            f"🎮 [{site_label} 가격 알림]\n\n"
            f"🕹 {result.name}\n"
            f"{price_line}\n"
            f"🔗 {result.url}"
        )