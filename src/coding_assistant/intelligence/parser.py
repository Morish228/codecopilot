"""Tree-sitter symbol extraction (Python MVP)."""

from dataclasses import dataclass
from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

_PY_LANGUAGE = Language(tspython.language())
_PARSER = Parser(_PY_LANGUAGE)


@dataclass(frozen=True)
class SymbolRecord:
    path: str
    kind: str
    name: str
    line_start: int
    line_end: int
    snippet: str


def extract_python_symbols(file_path: Path, workspace_root: Path) -> list[SymbolRecord]:
    source = file_path.read_text(encoding="utf-8", errors="replace")
    tree = _PARSER.parse(source.encode("utf-8"))
    rel = str(file_path.relative_to(workspace_root))
    lines = source.splitlines()
    records: list[SymbolRecord] = []

    def snippet_for(start: int, end: int) -> str:
        chunk = "\n".join(lines[start : end + 1])
        return chunk[:800]

    def walk(node):
        if node.type in ("function_definition", "async_function_definition"):
            name_node = node.child_by_field_name("name")
            if name_node:
                start, end = node.start_point.row, node.end_point.row
                records.append(
                    SymbolRecord(
                        path=rel,
                        kind="function",
                        name=source[name_node.start_byte : name_node.end_byte],
                        line_start=start + 1,
                        line_end=end + 1,
                        snippet=snippet_for(start, end),
                    )
                )
        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                start, end = node.start_point.row, node.end_point.row
                records.append(
                    SymbolRecord(
                        path=rel,
                        kind="class",
                        name=source[name_node.start_byte : name_node.end_byte],
                        line_start=start + 1,
                        line_end=end + 1,
                        snippet=snippet_for(start, end),
                    )
                )
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return records
