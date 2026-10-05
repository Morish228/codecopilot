from fastapi import APIRouter, Response

from coding_assistant.observability.metrics import metrics_enabled, render_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    if not metrics_enabled():
        return Response(status_code=404, content="Metrics disabled")
    return Response(content=render_metrics(), media_type="text/plain; version=0.0.4")
