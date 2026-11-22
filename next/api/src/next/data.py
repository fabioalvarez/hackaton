"""Orders data: models and the repository that reads them from disk."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class DataError(Exception):
    """The data file is missing, unreadable or invalid."""


class Order(BaseModel):
    id: str
    zone: str
    status: Literal["pending", "preparing", "in_transit", "delivered"]


class OrdersData(BaseModel):
    """Content of the data file. Also used as the `/orders` response."""

    data_version: str = Field(min_length=1)
    orders: list[Order]


class OrderRepository:
    """Reads the orders file on every call, so it keeps no state."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> OrdersData:
        try:
            return OrdersData.model_validate_json(self._path.read_bytes())
        except (OSError, ValidationError) as error:
            raise DataError(str(error)) from error
