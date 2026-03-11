"""
A sample library for basic geometric calculations.
Used to test the multi-agent documentation workflow.
"""

import math
from typing import Optional


def circle_area(radius: float) -> float:
    if radius < 0:
        raise ValueError("Radius cannot be negative")
    return math.pi * radius ** 2


def rectangle_perimeter(width: float, height: float) -> float:
    return 2 * (width + height)


def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))


class Shape:
    def __init__(self, name: str, color: str = "white"):
        self.name = name
        self.color = color

    def describe(self) -> str:
        return f"{self.color} {self.name}"

    def area(self) -> float:
        raise NotImplementedError("Subclasses must implement area()")


class Triangle(Shape):
    def __init__(self, base: float, height: float, color: str = "white"):
        super().__init__("triangle", color)
        self.base = base
        self.height = height

    def area(self) -> float:
        return 0.5 * self.base * self.height

    def hypotenuse(self) -> Optional[float]:
        if self.base <= 0 or self.height <= 0:
            return None
        return math.sqrt(self.base ** 2 + self.height ** 2)
