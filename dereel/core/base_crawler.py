from abc import ABC, abstractmethod

import httpx
from loguru import logger


class BaseCrawler(ABC):

    site_name: str = ""

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()

    @abstractmethod
    async def fetch(self, url: str) -> list:
        """URL을 크롤링해 StockResult 리스트를 반환한다."""

    async def _get(self, url: str) -> str:
        logger.debug(f"[{self.site_name}] GET {url}")
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.text
