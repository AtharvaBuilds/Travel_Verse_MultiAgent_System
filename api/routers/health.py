"""Health check router."""

import os
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])

_IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
_IMAGES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend", "images"
)


@router.get("/health", summary="Health check")
async def health_check() -> dict:
    """Returns service status and API key configuration."""
    return {
        "status": "ok",
        "service": "Travel Planner AI",
        "version": "1.0.0",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "aviation_configured": bool(os.getenv("avaiation_access_key")),
        "ninjas_configured": bool(os.getenv("API_NINJAS_KEY")),
    }


@router.get("/images", summary="List gallery images")
async def list_images() -> dict:
    """Scans frontend/images recursively and returns all image URLs grouped by subfolder."""
    result: dict[str, list[str]] = {}
    if not os.path.isdir(_IMAGES_DIR):
        return {"images": [], "by_folder": {}}

    all_urls: list[str] = []
    for root, _, files in os.walk(_IMAGES_DIR):
        folder = os.path.relpath(root, _IMAGES_DIR).replace("\\", "/")
        urls = []
        for f in sorted(files):
            if os.path.splitext(f)[1].lower() in _IMG_EXTS:
                rel = os.path.relpath(os.path.join(root, f), _IMAGES_DIR).replace("\\", "/")
                url = f"/static/images/{rel}"
                urls.append(url)
                all_urls.append(url)
        if urls:
            result[folder] = urls

    return {"images": all_urls, "by_folder": result}
