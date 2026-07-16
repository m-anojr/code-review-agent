from dataclasses import dataclass
from typing import Optional


@dataclass
class Rectangle:
    width: float
    height: float

    def area(self) -> float:
        return self.width * self.height

    def perimeter(self) -> float:
        return 2 * (self.width + self.height)

    def scale(self, factor: float) -> "Rectangle":
        return Rectangle(self.width * factor, self.height * factor)


def merge_dicts(base: dict, override: dict) -> dict:
    """Merge two dictionaries, with override taking precedence."""
    result = dict(base)
    result.update(override)
    return result


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value to the given range."""
    return max(min_val, min(value, max_val))
