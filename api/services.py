"""
Travel Planner Service Layer
Wraps the original multi-agent system for FastAPI.
Original files (TravelPlanner_Multi_agent_Ai.py, travel_agent_helper_apis.py) are NOT modified.
"""

import asyncio
import json
import sys
import os
import uuid
from typing import AsyncGenerator, Any, Optional

# Add project root to path so original modules can be imported unchanged
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Import original agents (do NOT modify these files) ─────────────────────
from TravelPlanner_Multi_agent_Ai import (
    destination_agent,
    flight_agent,
    weather_agent,
    exchange_rate_agent,
    budget_calculation_agent,
    itinerary_agent,
    llm,
)

from api.models import TripRequest

# ── Copilot system prompt with guardrails ──────────────────────────────────
_COPILOT_PROMPT = """You are an AI Travel Copilot embedded in a multi-agent travel planning app.

YOUR ROLE — only help with travel topics:
- Trip planning and itinerary adjustments
- Destination info and recommendations
- Budget optimisation and savings tips
- Flight and accommodation suggestions
- Weather and packing advice
- Visa, documentation, and travel requirements
- Local culture, food, and activities
- Safety tips for travellers

STRICT GUARDRAIL:
If a user asks about ANYTHING outside travel (coding, sports, politics, entertainment,
general knowledge, math, etc.) respond ONLY with:
"I'm your Travel Copilot, so I can only help with travel-related questions! 🗺️
Ask me about your destination, itinerary, budget, flights, weather, or packing tips."

Do NOT attempt to partially answer non-travel questions.

CURRENT TRIP CONTEXT:
{context}

Be helpful, concise and friendly. Use emojis sparingly."""


class TravelPlannerService:
    """Orchestrates original agents and streams progress via SSE."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    # ── Trip management ────────────────────────────────────────────────────

    def create_trip(self, request: TripRequest) -> str:
        trip_id = str(uuid.uuid4())
        self._store[trip_id] = {"request": request, "status": "created", "result": None, "error": None}
        return trip_id

    def get_result(self, trip_id: str) -> dict[str, Any]:
        trip = self._store.get(trip_id)
        if not trip:
            return {"trip_id": trip_id, "status": "not_found", "error": "Trip not found"}
        return {"trip_id": trip_id, "status": trip["status"], "result": trip.get("result"), "error": trip.get("error")}

    # ── SSE streaming ──────────────────────────────────────────────────────

    async def stream_trip_progress(self, trip_id: str) -> AsyncGenerator[str, None]:
        """
        Runs each agent individually and yields SSE events.
        Events: agent_start | agent_complete | agent_error | complete | error
        """
        trip = self._store.get(trip_id)
        if not trip:
            yield self._sse({"event": "error", "message": "Trip not found"})
            return

        request: TripRequest = trip["request"]

        # Build initial state matching original TravelAgentState
        state: dict[str, Any] = {
            "origin_city": request.origin_city,
            "destination_city": request.destination_city,
            "budget": request.budget,          # INR — matches original logic
            "no_of_nights": request.no_of_nights,
            "completed_tasks": [],
        }

        # Sequential order mirrors the supervisor's natural ordering
        agent_sequence = [
            ("destination",        "Researching destination & airports",     destination_agent),
            ("flight",             "Searching for available flights",         flight_agent),
            ("weather",            "Checking weather conditions",             weather_agent),
            ("exchange_rate",      "Fetching currency exchange rates",        exchange_rate_agent),
            ("budget_calculation", "Calculating your budget in USD",          budget_calculation_agent),
            ("itinerary",          "Creating your personalised itinerary",    itinerary_agent),
        ]

        loop = asyncio.get_running_loop()

        for key, label, func in agent_sequence:
            yield self._sse({"event": "agent_start", "agent": key, "label": label})
            try:
                result = await loop.run_in_executor(None, func, state)
                state.update(result)
                yield self._sse({"event": "agent_complete", "agent": key, "label": label})
            except Exception as exc:
                yield self._sse({"event": "agent_error", "agent": key, "label": label, "error": str(exc)})
                # Continue with remaining agents; partial results are still useful
            await asyncio.sleep(0.05)   # ensure event flushes

        serialized = self._serialize(state, request)
        self._store[trip_id]["result"] = serialized
        self._store[trip_id]["status"] = "completed"
        yield self._sse({"event": "complete", "result": serialized})

    # ── Copilot ────────────────────────────────────────────────────────────

    async def chat_with_copilot(self, message: str, trip_context: Optional[dict] = None) -> dict:
        context_str = self._build_context(trip_context)
        system_prompt = _COPILOT_PROMPT.format(context=context_str)
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": message}]
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: llm.invoke(messages))
            reply = response.content
        except Exception:
            reply = "I'm having trouble connecting right now. Please try again in a moment. 🔄"
        return {"reply": reply, "suggested_actions": self._quick_actions(trip_context)}

    # ── Private helpers ────────────────────────────────────────────────────

    def _sse(self, data: dict) -> str:
        return f"data: {json.dumps(data, default=str)}\n\n"

    def _build_context(self, ctx: Optional[dict]) -> str:
        if not ctx:
            return "No trip has been planned yet. Help the user plan a trip."
        lines = [
            f"Destination: {ctx.get('destination_city')} (from {ctx.get('origin_city')})",
            f"Duration: {ctx.get('no_of_nights')} nights",
            f"Budget: ₹{ctx.get('budget_inr')} (≈ ${ctx.get('budget_usd', 0):.0f} USD)",
            f"Exchange Rate: {ctx.get('exchange_rate_summary', 'N/A')}",
            f"Weather: {ctx.get('weather_summary', 'N/A')}",
            f"Flights: {ctx.get('flights_summary', 'N/A')}",
        ]
        itinerary = ctx.get("itinerary", "")
        if itinerary:
            lines.append(f"Itinerary:\n{itinerary[:2000]}")
        return "\n".join(lines)

    def _quick_actions(self, ctx: Optional[dict]) -> list[str]:
        if not ctx:
            return ["How do I choose a destination?", "What budget do I need?",
                    "What documents are required?", "Best time to travel?"]
        dest = ctx.get("destination_city", "my destination")
        return [
            f"Top attractions in {dest}?",
            "How can I save money on this trip?",
            f"What to pack for {dest}?",
            "Any visa requirements?",
        ]

    def _serialize(self, state: dict, request: TripRequest) -> dict:
        """Convert agent state to clean JSON-serialisable dict for the frontend."""
        weather_raw = state.get("weather") or {}
        weather_data = {
            "current": weather_raw.get("current", {}),
            "current_units": weather_raw.get("current_units", {}),
            "daily": weather_raw.get("daily", {}),
            "daily_units": weather_raw.get("daily_units", {}),
        }

        flights_raw = state.get("flights") or {}
        raw_list = flights_raw.get("data", []) if isinstance(flights_raw, dict) else []
        clean_flights = []
        for f in (raw_list or []):
            if not isinstance(f, dict):
                continue
            clean_flights.append({
                "airline":           (f.get("airline") or {}).get("name", "Unknown"),
                "airline_iata":      (f.get("airline") or {}).get("iata", ""),
                "flight_number":     (f.get("flight") or {}).get("number", ""),
                "flight_iata":       (f.get("flight") or {}).get("iata", ""),
                "departure_airport": (f.get("departure") or {}).get("airport", ""),
                "departure_iata":    (f.get("departure") or {}).get("iata", ""),
                "departure_time":    (f.get("departure") or {}).get("scheduled", ""),
                "arrival_airport":   (f.get("arrival") or {}).get("airport", ""),
                "arrival_iata":      (f.get("arrival") or {}).get("iata", ""),
                "arrival_time":      (f.get("arrival") or {}).get("scheduled", ""),
                "status":            f.get("flight_status", "scheduled"),
            })

        return {
            # Trip basics
            "origin_city":               state.get("origin_city"),
            "destination_city":          state.get("destination_city"),
            "budget_inr":                state.get("budget"),
            "no_of_nights":              state.get("no_of_nights"),
            "start_date":                request.start_date,
            "travelers":                 request.travelers,
            "accommodation_preference":  request.accommodation_preference,
            # Destination
            "destination_location":      state.get("destination_location", {}),
            "destination_summary":       state.get("destination_summary", ""),
            "departure_iata":            state.get("departure_iata", ""),
            "arrival_iata":              state.get("arrival_iata", ""),
            # Flights
            "flights":                   clean_flights,
            "flights_summary":           state.get("flights_summary", ""),
            # Weather
            "weather":                   weather_data,
            "weather_summary":           state.get("weather_summary", ""),
            # Exchange & Budget (INR → USD, matching original agent logic)
            "exchange_rate":             state.get("exchange_rate", 0),
            "exchange_rate_summary":     state.get("exchange_rate_summary", ""),
            "budget_usd":                state.get("budget_usd", 0),
            "budget_summary":            state.get("budget_summary", ""),
            # Itinerary
            "itinerary":                 state.get("itinerary", ""),
            # Meta
            "completed_tasks":           state.get("completed_tasks", []),
        }


# Global singleton used by all routers
travel_service = TravelPlannerService()
