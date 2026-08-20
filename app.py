"""Render/Gunicorn entrypoint for Nexora.

The Flask application lives in backend/app.py. app_extra adds the application
routes, and cors_runtime adds a final CORS layer that accepts the current
Vercel deployment (including preview URLs).
"""

from backend.app import *  # noqa: F401,F403
from backend import app_extra  # noqa: F401
from backend import cors_runtime  # noqa: F401
