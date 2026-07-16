import logging
from enum import Enum
from typing import List

logger = logging.getLogger(__name__)


class Status(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"


def filter_by_status(items: List[dict], status: Status) -> List[dict]:
    """Filter a list of items by their status field."""
    return [item for item in items if item.get("status") == status.value]


def safe_divide(a: float, b: float) -> float | None:
    """Divide a by b, returning None if b is zero."""
    if b == 0:
        logger.warning("Division by zero attempted: %s / %s", a, b)
        return None
    return a / b


def chunk_list(items: list, size: int) -> list[list]:
    """Split a list into chunks of the given size."""
    if size <= 0:
        raise ValueError("Chunk size must be positive")
    return [items[i : i + size] for i in range(0, len(items), size)]
