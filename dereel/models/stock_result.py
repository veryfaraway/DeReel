from datetime import datetime, timezone
from pydantic import BaseModel, Field


class StockResult(BaseModel):
    site: str
    product_id: str
    name: str
    price: float
    currency: str
    in_stock: bool
    url: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
