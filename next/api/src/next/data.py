"""Orders data: models and the repository that reads them from disk."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from next.errors import DataError


class Order(BaseModel):
    id: str
    zone: str
    status: Literal["pending", "preparing", "in_transit", "delivered"]


class OrdersData(BaseModel):
    """Content of the data file."""

    data_version: str = Field(min_length=1)
    orders: list[Order]


class OrdersResponse(BaseModel):
    """The `/orders` response: the orders only. Their version travels in the X-Data-Version header."""

    orders: list[Order]


class OrderRepository:
    """Reads the orders file on every call, so it keeps no state."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> OrdersData:
        try:
            data = self._path.read_bytes()
            
            return OrdersData.model_validate_json(data)
        except (OSError, ValidationError) as error:
            raise DataError(str(error)) from error
