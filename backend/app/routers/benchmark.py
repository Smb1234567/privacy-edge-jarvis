from fastapi import APIRouter

from ..core.metrics import snapshot_system_metrics

router = APIRouter(tags=["benchmark"])


@router.get("/benchmark/metrics")
def benchmark_metrics() -> dict:
    return snapshot_system_metrics()
