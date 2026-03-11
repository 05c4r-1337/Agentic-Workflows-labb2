"""
Entry point for the multi-agent code documentation workflow.

Usage:
    python main.py <path_to_source_file> [output_directory] [--baseline]

Supported languages:
    .py   Python
    .cs   C#

Examples:
    python main.py sample_code/example.py docs/
    python main.py sample_code/example.py docs/ --baseline
"""

import sys
import argparse
from pathlib import Path
from orchestrator import Orchestrator
from tools.parsers import SUPPORTED_EXTENSIONS


def main():
    parser = argparse.ArgumentParser(
        description="Multi-agent code documentation workflow"
    )
    parser.add_argument("target", help="Path to the source file to document")
    parser.add_argument("output_dir", nargs="?", default=".", help="Output directory (default: .)")
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Run in baseline mode: single DocWriter pass, no review loop or fact-checking",
    )
    args = parser.parse_args()

    if not Path(args.target).exists():
        print(f"Error: File not found: {args.target}")
        sys.exit(1)

    ext = Path(args.target).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        print(f"Error: Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        sys.exit(1)

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    orchestrator = Orchestrator(
        target_file=args.target,
        output_dir=args.output_dir,
        baseline=args.baseline,
    )
    orchestrator.run()


if __name__ == "__main__":
    main()
