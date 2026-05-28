from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class Storage(ABC):

    @abstractmethod
    def load_state(self, site: str) -> dict[str, Any]: ...

    @abstractmethod
    def save_state(self, site: str, state: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_last_crawled_at(self, key: str) -> datetime | None: ...

    @abstractmethod
    def save_crawled_at(self, key: str, timestamp: datetime) -> None: ...

    @abstractmethod
    def get_alert_record(self, key: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def save_alert_record(self, key: str, timestamp: datetime, price: float | None = None) -> None: ...

    @abstractmethod
    def get_consecutive_failures(self, site: str) -> int: ...

    @abstractmethod
    def increment_failures(self, site: str, error_message: str) -> int: ...

    @abstractmethod
    def reset_failures(self, site: str) -> None: ...
