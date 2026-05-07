# dereel/models/price_result.py
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class PriceResult(BaseModel):
    site: str
    product_id: str
    name: str
    original_price: float
    current_price: float
    currency: str
    url: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_free(self) -> bool:
        return self.current_price == 0

    def should_notify(self, target_price: float) -> bool:
        """무료 전환 또는 목표가 이하 시 True"""
        if self.is_free:
            return True
        return self.current_price <= target_price
