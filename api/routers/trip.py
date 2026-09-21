"""Trip planning router — plan, stream, result."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.models import TripRequest, TripInitResponse, TripResultResponse
from api.services import travel_service

router = APIRouter(prefix="/api/trip", tags=["trip"])


@router.post("/plan", response_model=TripInitResponse, summary="Start trip planning")
async def plan_trip(request: TripRequest) -> TripInitResponse:
    """
    Submit trip details to start the multi-agent planning process.
    Returns a trip_id — connect to /api/trip/stream/{trip_id} for live progress.
    """
    try:
        trip_id = travel_service.create_trip(request)
        return TripInitResponse(
            trip_id=trip_id,
            status="created",
            message=f"Planning started. Stream at /api/trip/stream/{trip_id}",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stream/{trip_id}", summary="Stream agent progress (SSE)")
async def stream_trip(trip_id: str):
    """
    Server-Sent Events stream of agent execution.
    Events: agent_start | agent_complete | agent_error | complete | error
    """
    return StreamingResponse(
        travel_service.stream_trip_progress(trip_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.get("/result/{trip_id}", response_model=TripResultResponse, summary="Get trip result (polling)")
async def get_trip_result(trip_id: str) -> TripResultResponse:
    """Polling fallback — returns 'created' or 'completed' status with result."""
    data = travel_service.get_result(trip_id)
    return TripResultResponse(**data)
