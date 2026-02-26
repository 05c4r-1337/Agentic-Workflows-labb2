"""
Entry point for the multi-agent code documentation workflow.

Usage:
    python main.py <path_to_python_file> [output_directory]

Example:
    python main.py sample_code/example.py docs/
"""

import sys
from pathlib import Path
from orchestrator import Orchestrator


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_python_file> [output_directory]")
        print("Example: python main.py sample_code/example.py docs/")
        sys.exit(1)

    target = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."

    if not Path(target).exists():
        print(f"Error: File not found: {target}")
        sys.exit(1)

    if not target.endswith(".py"):
        print(f"Warning: {target} does not appear to be a Python file.")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    orchestrator = Orchestrator(target_file=target, output_dir=output_dir)
    orchestrator.run()


if __name__ == "__main__":
    main()
