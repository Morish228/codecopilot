# Phase 3 — Tool System

**Status:** Complete  
**Date:** 2026-06-03

## Goal

Schema-driven tools with strict JSON Schema, host validation, and deterministic outputs.

## Tool contract

Every tool exposes:

```json
{
  "name": "read_file",
  "description": "...",
  "schema": { "type": "object", "additionalProperties": false, ... },
  "output_schema": { ... }
}
```

Rules enforced:

- `additionalProperties: false` on all object nodes (input and output)
- Required fields derived from Pydantic models
- Validation via JSON Schema + Pydantic before execution
- Outputs serialized through output models (`tools/outputs.py`)

## Architecture

```text
StructuredAction
      │
      ▼
ToolExecutor
      │
      ├── validate_tool_arguments()  (jsonschema + Pydantic)
      └── RegisteredTool.execute()
              │
              ├── builtin handler
              └── serialize_output()
```

## Code map

| Module | Role |
| ------ | ---- |
| `tools/base.py` | `RegisteredTool` dataclass |
| `tools/registry.py` | Single registry + `openai_tool_specs()` |
| `tools/schema_builder.py` | Strict JSON Schema generation |
| `tools/validation.py` | Host validation gate |
| `tools/builtin.py` | Tool implementations |
| `tools/outputs.py` | Deterministic output models |
| `tools/paths.py` / `tools/errors.py` | Shared security helpers |

## API

`GET /v1/tools` returns `schema` and `output_schema` per tool.

## Lint tool

Phase 3 implements real Python syntax checking via `ast.parse` (deterministic). Sandbox execution remains Phase 4.

## Next: Phase 4

Docker sandbox for `run_tests` and isolated command execution.
