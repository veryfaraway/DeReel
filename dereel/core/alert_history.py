from datetime import datetime, timedelta, timezone

from loguru import logger

from dereel.core.base_storage import Storage


class AlertHistory:

    def __init__(self, storage: Storage, cooldown_hours: int = 24) -> None:
        self._storage = storage
        self._cooldown = timedelta(hours=cooldown_hours)

    def can_alert(self, alert_key: str, current_price: float | None = None) -> bool:
        """쿨다운이 지났거나 가격이 직전 알림보다 낮으면 True, 이내면 False."""
        record = self._storage.get_alert_record(alert_key)
        if record is None:
            return True

        # 가격 하락 시 쿨다운 우회
        if current_price is not None and record.get("last_alerted_price") is not None:
            if current_price < record["last_alerted_price"]:
                logger.info(f"추가 가격 하락 감지 (직전: {record['last_alerted_price']} -> 현재: {current_price}). 쿨다운을 우회합니다.")
                return True

        last_sent = record.get("last_sent_at")
        if last_sent is None:
            return True

        elapsed = datetime.now(timezone.utc) - last_sent
        if elapsed >= self._cooldown:
            return True
        remaining = self._cooldown - elapsed
        logger.debug(f"쿨다운 중 — {alert_key} (남은 시간: {remaining})")
        return False

    def record(self, alert_key: str, current_price: float | None = None) -> None:
        """알림 발송 후 현재 시각과 가격을 기록한다."""
        self._storage.save_alert_record(alert_key, datetime.now(timezone.utc), current_price)

