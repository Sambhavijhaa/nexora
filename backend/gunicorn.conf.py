def post_worker_init(worker):
    # Render currently starts gunicorn with app:app. Import the extension module
    # after the main Flask app is loaded so its project/task routes are registered
    # on the exact same Flask application instance.
    import app_extra  # noqa: F401
