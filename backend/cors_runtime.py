"""Final CORS layer for the deployed Nexora frontend.

Vercel can serve the same project from several deployment URLs. The backend
must therefore accept the production nexora domains and Vercel preview URLs,
while still rejecting unrelated origins.
"""

import os
from flask import request
from app import app


EXTRA_ALLOWED = {
    item.strip().rstrip("/")
    for item in os.getenv("CORS_ORIGINS", "").split(",")
    if item.strip()
}


def is_allowed_origin(origin: str | None) -> bool:
    if not origin:
        return False
    origin = origin.rstrip("/")
    if origin in EXTRA_ALLOWED:
        return True
    if origin in {"https://nexora-ops.vercel.app", "https://nexora.vercel.app"}:
        return True
    return origin.startswith("https://") and origin.endswith(".vercel.app")


@app.after_request
def allow_deployed_frontend(response):
    origin = request.headers.get("Origin")
    if is_allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Request-ID, X-Workspace-ID"
        )
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response
