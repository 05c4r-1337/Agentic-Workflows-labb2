"""Parser factory — returns the right parser for a given file extension."""

from pathlib import Path
from tools.parsers.base_parser import BaseParser

SUPPORTED_EXTENSIONS = {".py", ".cs"}


def get_parser(file_path: str) -> BaseParser:
    ext = Path(file_path).suffix.lower()
    if ext == ".py":
        from tools.parsers.python_parser import PythonParser
        return PythonParser()
    if ext == ".cs":
        from tools.parsers.csharp_parser import CSharpParser
        return CSharpParser()
    raise ValueError(
        f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    )
