"""
FastAPI application entry point for the Travel Planner Multi-Agent System.
Original agent files are NOT modified — this file only adds the API layer.
"""

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from dotenv import load_dotenv

load_dotenv()

from api.routers import trip, copilot, health

app = FastAPI(
    title="Travel Planner AI",
    description=(
        "Multi-agent AI travel planning system powered by LangGraph + OpenAI. "
        "6 specialist agents collaborate to research destinations, find flights, "
        "check weather, convert budgets and craft personalised itineraries."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ───────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(trip.router)
app.include_router(copilot.router)

# ── Static / Frontend ──────────────────────────────────────────────────────
_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_frontend = os.path.join(_base, "frontend")

# MIME type map for common static file types
_MIME = {
    ".html": "text/html",
    ".css":  "text/css",
    ".js":   "application/javascript",
    ".json": "application/json",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif":  "image/gif",
    ".svg":  "image/svg+xml",
    ".ico":  "image/x-icon",
    ".woff2":"font/woff2",
    ".woff": "font/woff",
}

_NO_CACHE = "no-cache, no-store, must-revalidate"

if os.path.isdir(_frontend):

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        path = os.path.join(_frontend, "index.html")
        return FileResponse(path, headers={"Cache-Control": _NO_CACHE})

    @app.get("/static/{file_path:path}", include_in_schema=False)
    async def serve_static(file_path: str):
        abs_path = os.path.join(_frontend, file_path)
        if not os.path.isfile(abs_path):
            return Response(content="Not Found", status_code=404)
        ext = os.path.splitext(abs_path)[1].lower()
        media_type = _MIME.get(ext, "application/octet-stream")
        return FileResponse(abs_path, media_type=media_type,
                            headers={"Cache-Control": _NO_CACHE})
