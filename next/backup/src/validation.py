"""Validation of the data file. Same rules as the API."""

import json
import re
from pathlib import Path

STATUSES = {"pending", "preparing", "in_transit", "delivered"}

# The version becomes part of a file name, so only safe characters are accepted.
VERSION_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def get_data_version(path: Path) -> str | None:
    """Version of the data file if the file is valid, None otherwise."""
    try:
        data = json.loads(path.read_text())
        version, orders = data["data_version"], data["orders"]
    except (OSError, ValueError, KeyError, TypeError):
        return None

    valid = (
        isinstance(version, str)
        and VERSION_PATTERN.match(version)
        and isinstance(orders, list)
        and all(
            isinstance(order, dict)
            and isinstance(order.get("id"), str)
            and isinstance(order.get("zone"), str)
            and order.get("status") in STATUSES
            for order in orders
        )
    )

    return version if valid else None
