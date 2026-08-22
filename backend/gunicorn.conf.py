"""Gunicorn production bootstrap for Nexora."""

import logging


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def post_worker_init(worker):
    # Import the real Flask application directly. The stable_entrypoint layer
    # depended on helpers that are no longer part of app.py and caused workers
    # to crash before serving any request.
    from app import app

    # Install the small workspace/activity runtime patch after the app exists.
    # It does not replace the main application or reset the database.
    import workspace_runtime  # noqa: F401

    # Keep request_id logging safe for Gunicorn/Flask records that are emitted
    # outside the normal request lifecycle.
    request_id_filter = RequestIdFilter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(request_id_filter)
    for logger in list(logging.Logger.manager.loggerDict.values()):
        if isinstance(logger, logging.Logger):
            for handler in logger.handlers:
                handler.addFilter(request_id_filter)

    # The API root is useful for Render health checks and manual diagnostics.
    if not any(rule.rule == "/" for rule in app.url_map.iter_rules()):
        @app.get("/")
        def service_root():
            return {
                "success": True,
                "service": "Nexora API",
                "status": "online",
                "health": "/api/health",
            }
