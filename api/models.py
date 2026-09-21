"""Pydantic models for Travel Planner AI API."""

from pydantic import BaseModel, Field
from typing import Optional, Any


class TripRequest(BaseModel):
    origin_city: str = Field(..., description="City of departure")
    destination_city: str = Field(..., description="Destination city")
    budget: float = Field(..., gt=0, description="Total budget in INR")
    no_of_nights: int = Field(..., gt=0, description="Number of nights")
    start_date: Optional[str] = Field(None, description="Trip start date (YYYY-MM-DD)")
    travelers: Optional[int] = Field(1, ge=1, le=50, description="Number of travelers")
    accommodation_preference: Optional[str] = Field(
        "any",
        description="Accommodation: any | budget | mid-range | luxury"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "origin_city": "Mumbai",
                "destination_city": "Dubai",
                "budget": 150000,
                "no_of_nights": 5,
                "start_date": "2026-10-15",
                "travelers": 2,
                "accommodation_preference": "mid-range"
            }
        }
    }


class TripInitResponse(BaseModel):
    trip_id: str
    status: str
    message: str


class TripResultResponse(BaseModel):
    trip_id: str
    status: str
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class CopilotRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    trip_context: Optional[dict[str, Any]] = Field(
        None, description="Current trip result for personalised responses"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "What should I pack for Dubai?",
                "trip_context": {"destination_city": "Dubai", "no_of_nights": 5}
            }
        }
    }


class CopilotResponse(BaseModel):
    reply: str
    suggested_actions: list[str] = []
