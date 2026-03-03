"""C# source parser using tree-sitter."""

from memory.session_memory import DocEntry
from tools.parsers.base_parser import BaseParser

# Node types that represent type declarations
_TYPE_NODES = {"class_declaration", "interface_declaration", "struct_declaration"}

# Node types that represent callable/property members
_MEMBER_NODES = {"method_declaration", "constructor_declaration", "property_declaration"}


def _node_text(node) -> str:
    return node.text.decode("utf-8")


def _extract_lines(lines: list[str], node) -> str:
    start = node.start_point[0]
    end = node.end_point[0] + 1
    return "\n".join(lines[start:end])


def _get_signature(node) -> str:
    """Return the declaration up to (but not including) the opening brace."""
    text = _node_text(node)
    brace = text.find("{")
    if brace != -1:
        return text[:brace].strip()
    return text.splitlines()[0].strip()


def _walk_declarations(node, lines: list[str], entries: list[DocEntry], class_name: str = ""):
    for child in node.children:
        if child.type == "namespace_declaration":
            body = child.child_by_field_name("body")
            if body:
                _walk_declarations(body, lines, entries, class_name)

        elif child.type in _TYPE_NODES:
            name_node = child.child_by_field_name("name")
            name = _node_text(name_node) if name_node else "Unknown"
            entries.append(DocEntry(
                element_type="class",
                name=name,
                signature=_get_signature(child),
                source_code=_extract_lines(lines, child),
            ))
            body = child.child_by_field_name("body")
            if body:
                _walk_declarations(body, lines, entries, class_name=name)

        elif child.type in _MEMBER_NODES:
            name_node = child.child_by_field_name("name")
            name = _node_text(name_node) if name_node else child.type
            full_name = f"{class_name}.{name}" if class_name else name
            element_type = "method" if class_name else "function"
            entries.append(DocEntry(
                element_type=element_type,
                name=full_name,
                signature=_get_signature(child),
                source_code=_extract_lines(lines, child),
            ))


class CSharpParser(BaseParser):
    def parse(self, source: str) -> list[DocEntry]:
        try:
            import tree_sitter_c_sharp as tscsharp
            from tree_sitter import Language, Parser
        except ImportError:
            raise RuntimeError(
                "tree-sitter and tree-sitter-c-sharp are required for C# support. "
                "Install them with: pip install tree-sitter tree-sitter-c-sharp"
            )

        parser = Parser(Language(tscsharp.language()))
        tree = parser.parse(source.encode("utf-8"))
        root = tree.root_node
        lines = source.splitlines()
        entries: list[DocEntry] = []

        # Module/namespace entry
        namespace_nodes = [n for n in root.children if n.type == "namespace_declaration"]
        if namespace_nodes:
            ns = namespace_nodes[0]
            name_node = ns.child_by_field_name("name")
            ns_name = _node_text(name_node) if name_node else "namespace"
            entries.append(DocEntry(
                element_type="module",
                name=ns_name,
                signature=f"namespace {ns_name}",
                source_code="\n".join(lines[:min(20, len(lines))]),
            ))
        else:
            entries.append(DocEntry(
                element_type="module",
                name="module",
                signature="(file level)",
                source_code="\n".join(lines[:min(20, len(lines))]),
            ))

        _walk_declarations(root, lines, entries)
        return entries
