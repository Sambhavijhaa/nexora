def post_worker_init(worker):
    # Load the runtime API extensions after app:app is initialized.
    # Do not import the legacy app_extra module: it registers duplicate Flask
    # routes and makes gunicorn workers fail to boot.
    import runtime_extensions  # noqa: F401
