from abc import ABC, abstractmethod
from typing import Any

from loguru import logger


class BaseCrawler(ABC):

    site_name: str = ""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    @abstractmethod
    async def fetch(self) -> Any:
        """사이트에서 원본 데이터를 가져온다."""

    @abstractmethod
    def parse(self, raw_data: Any) -> list[Any]:
        """원본 데이터를 Result 리스트로 변환한다."""

    @abstractmethod
    def format_message(self, diff: dict[str, Any]) -> str:
        """Telegram 알림 메시지를 생성한다."""

    async def run(self) -> None:
        """fetch → parse 전체 흐름 실행."""
        logger.info(f"[{self.site_name}] 크롤링 시작")
        try:
            raw = await self.fetch()
            results = self.parse(raw)
            logger.info(f"[{self.site_name}] 파싱 완료 — {len(results)}건")
            return results
        except Exception as e:
            logger.error(f"[{self.site_name}] 실행 실패 — {e}")
            raise
