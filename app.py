"""Render/Gunicorn entrypoint for Nexora.

Render starts the service with `gunicorn app:app` from the repository root.
The actual Flask application lives in backend/app.py; app_extra.py registers
workspace-aware routes on that same Flask instance.
"""

from backend.app import *  # noqa: F401,F403
from backend import app_extra  # noqa: F401
