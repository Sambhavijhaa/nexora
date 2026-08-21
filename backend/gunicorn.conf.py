"""Gunicorn bootstrap for the production Nexora API."""


def post_worker_init(worker):
    # Render currently runs `gunicorn app:app`. Load the workspace-aware
    # runtime after Flask has been imported so that deployment settings cannot
    # accidentally expose only the legacy routes.
    from app import app
    import runtime_v2  # noqa: F401
    import workspace_legacy_fix  # noqa: F401

    if not any(rule.rule == "/" for rule in app.url_map.iter_rules()):
        @app.get("/")
        def service_root():
            return {
                "success": True,
                "service": "Nexora API",
                "status": "online",
                "health": "/api/health",
            }
