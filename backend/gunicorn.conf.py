"""Gunicorn production bootstrap for Nexora."""

import logging


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def post_worker_init(worker):
    # stable_entrypoint initializes app_extra and installs the workspace-aware
    # handlers in the correct order. Do NOT import runtime_v2 directly here:
    # runtime_v2 expects app.membership_for to already exist and otherwise
    # crashes the Gunicorn worker during boot.
    import stable_entrypoint  # noqa: F401
    from app import app

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
