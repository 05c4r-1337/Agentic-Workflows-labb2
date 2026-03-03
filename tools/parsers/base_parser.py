"""Abstract base class for all language parsers."""

from abc import ABC, abstractmethod
from memory.session_memory import DocEntry


class BaseParser(ABC):
    @abstractmethod
    def parse(self, source: str) -> list[DocEntry]:
        """Parse source code and return a list of DocEntry objects."""
        ...
