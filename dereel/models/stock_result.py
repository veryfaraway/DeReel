from datetime import datetime
from pydantic import BaseModel


class StockResult(BaseModel):
    site: str
    product_id: str
    name: str
    price: int
    currency: str
    in_stock: bool
    url: str
    fetched_at: datetime
