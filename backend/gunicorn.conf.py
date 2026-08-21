"""Gunicorn bootstrap for the production Nexora API."""

import logging

from flask_jwt_extended import jwt_required


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def post_worker_init(worker):
    # Render currently runs `gunicorn app:app`. Load the workspace-aware
    # runtime after Flask has been imported so deployment uses the same routes
    # as the frontend.
    from app import app
    import runtime_v2
    import workspace_legacy_fix  # noqa: F401

    # runtime_v2 replaces the legacy handlers by endpoint name, but its
    # workspace-sensitive handlers must still require a valid JWT. Without
    # this wrapper get_jwt_identity() raises RuntimeError and every dashboard
    # page receives HTTP 500.
    protected_runtime_handlers = {
        "get_team": runtime_v2.get_team_runtime,
        "get_projects": runtime_v2.get_projects_runtime,
        "get_tasks": runtime_v2.get_tasks_runtime,
        "dashboard_summary": runtime_v2.get_dashboard_runtime,
        "analytics": runtime_v2.get_analytics_runtime,
        "get_activity": runtime_v2.get_activity_runtime,
        "get_workspace": runtime_v2.get_selected_workspace,
    }
    for endpoint, handler in protected_runtime_handlers.items():
        app.view_functions[endpoint] = jwt_required()(handler)

    # Keep request_id logging safe for exceptions raised outside a request
    # context (Gunicorn/Flask can emit those records without the request
    # lifecycle's extra field).
    request_id_filter = RequestIdFilter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(request_id_filter)
    for logger in list(logging.Logger.manager.loggerDict.values()):
        if isinstance(logger, logging.Logger):
            for handler in logger.handlers:
                handler.addFilter(request_id_filter)

    if not any(rule.rule == "/" for rule in app.url_map.iter_rules()):
        @app.get("/")
        def service_root():
            return {
                "success": True,
                "service": "Nexora API",
                "status": "online",
                "health": "/api/health",
            }
