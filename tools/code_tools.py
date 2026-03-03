"""
Code analysis tools using Python's AST module.
Extracts functions, classes, and methods from source code.
"""

import ast
import textwrap
from memory.session_memory import DocEntry


def read_file(path: str) -> str:
    """Read a Python source file and return its contents."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_source(source: str, node: ast.AST) -> str:
    """Extract the source code lines for a given AST node."""
    lines = source.splitlines()
    start = node.lineno - 1
    end = node.end_lineno
    return "\n".join(lines[start:end])


def get_function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Build a human-readable function signature from an AST node."""
    args = []
    func_args = node.args

    # Positional args
    defaults_offset = len(func_args.args) - len(func_args.defaults)
    for i, arg in enumerate(func_args.args):
        annotation = ""
        if arg.annotation:
            annotation = f": {ast.unparse(arg.annotation)}"
        default_idx = i - defaults_offset
        if default_idx >= 0:
            default = f" = {ast.unparse(func_args.defaults[default_idx])}"
        else:
            default = ""
        args.append(f"{arg.arg}{annotation}{default}")

    # *args
    if func_args.vararg:
        annotation = ""
        if func_args.vararg.annotation:
            annotation = f": {ast.unparse(func_args.vararg.annotation)}"
        args.append(f"*{func_args.vararg.arg}{annotation}")

    # **kwargs
    if func_args.kwarg:
        annotation = ""
        if func_args.kwarg.annotation:
            annotation = f": {ast.unparse(func_args.kwarg.annotation)}"
        args.append(f"**{func_args.kwarg.arg}{annotation}")

    return_ann = ""
    if node.returns:
        return_ann = f" -> {ast.unparse(node.returns)}"

    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({', '.join(args)}){return_ann}"


def parse_code(source: str) -> list[DocEntry]:
    """
    Parse Python source code and return a list of DocEntry objects
    for each module, class, function, and method found.
    """
    tree = ast.parse(source)
    entries: list[DocEntry] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_source = extract_source(source, node)
            entries.append(DocEntry(
                element_type="class",
                name=node.name,
                signature=f"class {node.name}",
                source_code=class_source,
            ))

            # Methods inside the class
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_source = extract_source(source, item)
                    sig = get_function_signature(item)
                    entries.append(DocEntry(
                        element_type="method",
                        name=f"{node.name}.{item.name}",
                        signature=sig,
                        source_code=method_source,
                    ))

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Only top-level functions (not methods)
            parent_is_class = any(
                isinstance(p, ast.ClassDef) and node in ast.walk(p)
                for p in ast.walk(tree)
                if p is not node
            )
            if not parent_is_class:
                func_source = extract_source(source, node)
                sig = get_function_signature(node)
                entries.append(DocEntry(
                    element_type="function",
                    name=node.name,
                    signature=sig,
                    source_code=func_source,
                ))

    return entries


def write_markdown(content: str, path: str):
    """Write a string to a Markdown file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
