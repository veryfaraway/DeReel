import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path


class Storage(ABC):

    @abstractmethod
    def load_state(self, site: str) -> dict: ...

    @abstractmethod
    def save_state(self, site: str, state: dict) -> None: ...

    @abstractmethod
    def get_last_alert_time(self, key: str) -> datetime | None: ...

    @abstractmethod
    def save_alert_time(self, key: str, timestamp: datetime) -> None: ...

    @abstractmethod
    def get_last_crawled_at(self, key: str) -> datetime | None: ...

    @abstractmethod
    def save_crawled_at(self, key: str, timestamp: datetime) -> None: ...


class JsonStorage(Storage):
    """JSON 파일 기반 Storage 구현체."""

    def __init__(self, data_dir: str = "data") -> None:
        self._base = Path(data_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _state_path(self, site: str) -> Path:
        return self._base / f"{site}_state.json"

    def _alert_path(self, site: str) -> Path:
        return self._base / f"{site}_alerts.json"

    def _crawl_path(self) -> Path:
        return self._base / "crawl_schedule.json"

    # ── 재고 상태 ──────────────────────────────────────────

    def load_state(self, site: str) -> dict:
        path = self._state_path(site)
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    def save_state(self, site: str, state: dict) -> None:
        self._state_path(site).write_text(
            json.dumps(state, ensure_ascii=False, indent=2)
        )

    # ── 알림 이력 ──────────────────────────────────────────

    def get_last_alert_time(self, key: str) -> datetime | None:
        site = key.split(":")[0]
        path = self._alert_path(site)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        ts = data.get(key)
        if ts is None:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc)

    def save_alert_time(self, key: str, timestamp: datetime) -> None:
        site = key.split(":")[0]
        path = self._alert_path(site)
        data = json.loads(path.read_text()) if path.exists() else {}
        data[key] = timestamp.timestamp()
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    # ── 크롤링 스케줄 ──────────────────────────────────────

    def get_last_crawled_at(self, key: str) -> datetime | None:
        path = self._crawl_path()
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        ts = data.get(key)
        if ts is None:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc)

    def save_crawled_at(self, key: str, timestamp: datetime) -> None:
        path = self._crawl_path()
        data = json.loads(path.read_text()) if path.exists() else {}
        data[key] = timestamp.timestamp()
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
