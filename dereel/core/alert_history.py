from datetime import datetime, timedelta, timezone

from loguru import logger

from dereel.core.storage import Storage


class AlertHistory:

    def __init__(self, storage: Storage, cooldown_hours: int = 24) -> None:
        self._storage = storage
        self._cooldown = timedelta(hours=cooldown_hours)

    def can_alert(self, alert_key: str) -> bool:
        """쿨다운이 지났으면 True, 아직 이내면 False."""
        last = self._storage.get_last_alert_time(alert_key)
        if last is None:
            return True
        elapsed = datetime.now(timezone.utc) - last
        if elapsed >= self._cooldown:
            return True
        remaining = self._cooldown - elapsed
        logger.debug(f"쿨다운 중 — {alert_key} (남은 시간: {remaining})")
        return False

    def record(self, alert_key: str) -> None:
        """알림 발송 후 현재 시각을 기록한다."""
        self._storage.save_alert_time(alert_key, datetime.now(timezone.utc))
