import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger


class Storage(ABC):

    @abstractmethod
    def load_state(self, key: str) -> dict:
        """이전 상태를 불러온다."""

    @abstractmethod
    def save_state(self, key: str, data: dict) -> None:
        """현재 상태를 저장한다."""

    @abstractmethod
    def get_last_alert_time(self, alert_key: str) -> datetime | None:
        """마지막 알림 발송 시각을 반환한다."""

    @abstractmethod
    def save_alert_time(self, alert_key: str, dt: datetime) -> None:
        """알림 발송 시각을 저장한다."""


class JsonFileStorage(Storage):

    def __init__(self, data_dir: str = "./data") -> None:
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self._dir / "stock_state.json"
        self._alert_file = self._dir / "alert_history.json"

    def _read(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"파일 읽기 실패 {path} — {e}")
            return {}

    def _write(self, path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_state(self, key: str) -> dict:
        return self._read(self._state_file).get(key, {})

    def save_state(self, key: str, data: dict) -> None:
        state = self._read(self._state_file)
        state[key] = data
        self._write(self._state_file, state)
        logger.debug(f"상태 저장 완료 — {key}")

    def get_last_alert_time(self, alert_key: str) -> datetime | None:
        history = self._read(self._alert_file)
        raw = history.get(alert_key)
        if raw is None:
            return None
        return datetime.fromisoformat(raw)

    def save_alert_time(self, alert_key: str, dt: datetime) -> None:
        history = self._read(self._alert_file)
        history[alert_key] = dt.isoformat()
        self._write(self._alert_file, history)
        logger.debug(f"알림 이력 저장 — {alert_key}")
