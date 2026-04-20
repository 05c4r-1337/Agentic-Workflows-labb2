"""
Code analysis tools.
"""

def read_file(path: str) -> str:
    """Read a source file and return its contents."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_markdown(content: str, path: str):
    """Write a string to a Markdown file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)