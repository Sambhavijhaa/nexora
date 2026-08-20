def post_worker_init(worker):
    # Load workspace APIs only after app:app is fully initialized.
    # runtime_v2 replaces workspace-sensitive handlers without registering
    # duplicate legacy routes.
    import runtime_v2  # noqa: F401
