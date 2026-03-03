"""Python source parser using the built-in ast module."""

import ast
from memory.session_memory import DocEntry
from tools.parsers.base_parser import BaseParser


def _extract_source(source: str, node: ast.AST) -> str:
    lines = source.splitlines()
    return "\n".join(lines[node.lineno - 1 : node.end_lineno])


def _get_function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = []
    func_args = node.args

    defaults_offset = len(func_args.args) - len(func_args.defaults)
    for i, arg in enumerate(func_args.args):
        annotation = f": {ast.unparse(arg.annotation)}" if arg.annotation else ""
        default_idx = i - defaults_offset
        default = f" = {ast.unparse(func_args.defaults[default_idx])}" if default_idx >= 0 else ""
        args.append(f"{arg.arg}{annotation}{default}")

    if func_args.vararg:
        annotation = f": {ast.unparse(func_args.vararg.annotation)}" if func_args.vararg.annotation else ""
        args.append(f"*{func_args.vararg.arg}{annotation}")

    if func_args.kwarg:
        annotation = f": {ast.unparse(func_args.kwarg.annotation)}" if func_args.kwarg.annotation else ""
        args.append(f"**{func_args.kwarg.arg}{annotation}")

    return_ann = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({', '.join(args)}){return_ann}"


class PythonParser(BaseParser):
    def parse(self, source: str) -> list[DocEntry]:
        tree = ast.parse(source)
        entries: list[DocEntry] = []

        # Module entry
        module_source_lines = source.splitlines()
        entries.append(DocEntry(
            element_type="module",
            name="module",
            signature="(module level)",
            source_code="\n".join(module_source_lines[:min(20, len(module_source_lines))]),
        ))

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                entries.append(DocEntry(
                    element_type="class",
                    name=node.name,
                    signature=f"class {node.name}",
                    source_code=_extract_source(source, node),
                ))
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        entries.append(DocEntry(
                            element_type="method",
                            name=f"{node.name}.{item.name}",
                            signature=_get_function_signature(item),
                            source_code=_extract_source(source, item),
                        ))

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parent_is_class = any(
                    isinstance(p, ast.ClassDef) and node in ast.walk(p)
                    for p in ast.walk(tree)
                    if p is not node
                )
                if not parent_is_class:
                    entries.append(DocEntry(
                        element_type="function",
                        name=node.name,
                        signature=_get_function_signature(node),
                        source_code=_extract_source(source, node),
                    ))

        return entries
