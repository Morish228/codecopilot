"""Build strict JSON Schemas for tool definitions (Phase 3)."""

from typing import Any

from pydantic import BaseModel


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Produce an OpenAI-compatible parameters schema with additionalProperties=false throughout."""
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {}) or {}
    resolved = _resolve_refs(raw, defs)
    _apply_strict_objects(resolved)
    resolved.pop("$defs", None)
    return resolved


def _resolve_refs(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            key = ref.split("/")[-1]
            if key not in defs:
                return node
            merged = _resolve_refs(defs[key].copy(), defs)
            return merged
        return {k: _resolve_refs(v, defs) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_refs(item, defs) for item in node]
    return node


def _apply_strict_objects(node: Any) -> None:
    if isinstance(node, dict):
        if node.get("type") == "object" or "properties" in node:
            node["additionalProperties"] = False
            props = node.get("properties") or {}
            if props and "required" not in node:
                node["required"] = sorted(props.keys())
        for value in node.values():
            _apply_strict_objects(value)
    elif isinstance(node, list):
        for item in node:
            _apply_strict_objects(item)
