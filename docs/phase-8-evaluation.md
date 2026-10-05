# Phase 8 — Evaluation System

**Status:** Complete (MVP)  
**Date:** 2026-06-03

## Architecture

```text
evals/datasets/*.json → EvalRunner → tools (sandbox) → Grader → EvalReport
```

## Datasets

- `evals/datasets/smoke.json` — tool-level smoke cases
- Fixtures under `evals/datasets/fixtures/`

## API

- `GET /v1/evals/datasets`
- `POST /v1/evals/run/{dataset_name}`

## Metrics in report

Success rate, per-case pass/fail, average duration.

## Next: Phase 9

Hosted control plane (auth, tenancy, billing).
