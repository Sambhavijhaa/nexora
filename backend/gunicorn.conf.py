def post_worker_init(worker):
    # Render starts gunicorn with app:app. Load all extension routes against
    # the same Flask application instance.
    import app_extra  # noqa: F401
    import workspace_context_extra  # noqa: F401
