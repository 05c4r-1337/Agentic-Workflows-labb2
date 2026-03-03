"""
Entry point for the multi-agent code documentation workflow.

Usage:
    python main.py <path_to_source_file> [output_directory]

Supported languages:
    .py   Python
    .cs   C# (requires: pip install tree-sitter-languages)

Example:
    python main.py sample_code/example.py docs/
    python main.py sample_code/example.cs docs/
"""

import sys
from pathlib import Path
from orchestrator import Orchestrator
from tools.parsers import SUPPORTED_EXTENSIONS


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_source_file> [output_directory]")
        print(f"Supported file types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        sys.exit(1)

    target = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."

    if not Path(target).exists():
        print(f"Error: File not found: {target}")
        sys.exit(1)

    ext = Path(target).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        print(f"Error: Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        sys.exit(1)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    orchestrator = Orchestrator(target_file=target, output_dir=output_dir)
    orchestrator.run()


if __name__ == "__main__":
    main()
