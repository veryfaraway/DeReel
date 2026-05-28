import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dereel.core.base_storage import Storage


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

    def load_state(self, site: str) -> dict[str, Any]:
        path = self._state_path(site)
        if not path.exists():
            return {}
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    def save_state(self, site: str, state: dict[str, Any]) -> None:
        self._state_path(site).write_text(
            json.dumps(state, ensure_ascii=False, indent=2)
        )

    # ── 알림 이력 ──────────────────────────────────────────

    def get_alert_record(self, key: str) -> dict[str, Any] | None:
        site = key.split(":")[0]
        path = self._alert_path(site)
        if not path.exists():
            return None
        try:
            data: dict[str, Any] = json.loads(path.read_text())
        except Exception:
            return None

        val = data.get(key)
        if val is None:
            return None

        # 하위 호환성 유지: 기존에 단순 timestamp(float)로 저장되어 있던 경우 처리
        if isinstance(val, (int, float)):
            return {
                "last_sent_at": datetime.fromtimestamp(val, tz=UTC),
                "last_alerted_price": None,
            }
        if isinstance(val, dict):
            ts = val.get("last_sent_at")
            return {
                "last_sent_at": datetime.fromtimestamp(ts, tz=UTC) if ts else None,
                "last_alerted_price": val.get("last_alerted_price"),
            }
        return None

    def save_alert_record(self, key: str, timestamp: datetime, price: float | None = None) -> None:
        site = key.split(":")[0]
        path = self._alert_path(site)
        data: dict[str, Any] = json.loads(path.read_text()) if path.exists() else {}
        data[key] = {
            "last_sent_at": timestamp.timestamp(),
            "last_alerted_price": price,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    # ── 크롤링 스케줄 ──────────────────────────────────────

    def get_last_crawled_at(self, key: str) -> datetime | None:
        path = self._crawl_path()
        if not path.exists():
            return None
        try:
            data: dict[str, Any] = json.loads(path.read_text())
        except Exception:
            return None

        # 하위 호환성: 기존 플랫 딕셔너리 구조인 경우 처리
        if "schedules" not in data:
            ts = data.get(key)
        else:
            ts = data.get("schedules", {}).get(key)

        if ts is None:
            return None
        return datetime.fromtimestamp(float(ts), tz=UTC)

    def save_crawled_at(self, key: str, timestamp: datetime) -> None:
        path = self._crawl_path()
        data: dict[str, Any] = json.loads(path.read_text()) if path.exists() else {}

        # 하위 호환성 마이그레이션
        if "schedules" not in data and data:
            data = {"schedules": data, "failures": {}}
        elif not data:
            data = {"schedules": {}, "failures": {}}

        data["schedules"][key] = timestamp.timestamp()
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def get_consecutive_failures(self, site: str) -> int:
        path = self._crawl_path()
        if not path.exists():
            return 0
        try:
            data: dict[str, Any] = json.loads(path.read_text())
        except Exception:
            return 0
        return int(data.get("failures", {}).get(site, {}).get("consecutive_failures", 0))

    def increment_failures(self, site: str, error_message: str) -> int:
        path = self._crawl_path()
        data: dict[str, Any] = json.loads(path.read_text()) if path.exists() else {}

        # 하위 호환성 마이그레이션 및 초기화
        if "failures" not in data:
            data = {
                "schedules": data if "schedules" not in data else data.get("schedules", {}),
                "failures": {},
            }

        failures: dict[str, Any] = data["failures"]
        record: dict[str, Any] = failures.get(site, {"consecutive_failures": 0, "last_error_message": ""})
        new_count = int(record.get("consecutive_failures", 0)) + 1

        failures[site] = {
            "consecutive_failures": new_count,
            "last_error_message": error_message,
            "updated_at": datetime.now(UTC).isoformat(),
        }

        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        return new_count

    def reset_failures(self, site: str) -> None:
        path = self._crawl_path()
        if not path.exists():
            return
        try:
            data: dict[str, Any] = json.loads(path.read_text())
        except Exception:
            return

        # 하위 호환성 마이그레이션
        if "failures" not in data:
            data = {
                "schedules": data if "schedules" not in data else data.get("schedules", {}),
                "failures": {},
            }

        if site in data["failures"]:
            data["failures"][site] = {
                "consecutive_failures": 0,
                "last_error_message": "",
                "updated_at": datetime.now(UTC).isoformat(),
            }
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def get_storage(storage_type: str, data_dir: str = "data") -> Storage:
    """지정된 스토리지 타입에 맞는 저장소 객체를 반환하는 팩토리 함수."""
    if storage_type.lower() == "json":
        return JsonStorage(data_dir=data_dir)
    raise ValueError(f"지원하지 않는 스토리지 타입: {storage_type}")
