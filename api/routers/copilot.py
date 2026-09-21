"""AI Travel Copilot router."""

from fastapi import APIRouter, HTTPException

from api.models import CopilotRequest, CopilotResponse
from api.services import travel_service

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


@router.post("/chat", response_model=CopilotResponse, summary="Chat with AI Travel Copilot")
async def chat(request: CopilotRequest) -> CopilotResponse:
    """
    AI copilot with travel-only guardrails.
    Pass trip_context (from the plan result) for personalised answers.
    Off-topic queries are gracefully declined.
    """
    try:
        result = await travel_service.chat_with_copilot(
            message=request.message,
            trip_context=request.trip_context,
        )
        return CopilotResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
