"""Load Nexora runtime fixes when Gunicorn imports app:app."""
import builtins

_original_import = builtins.__import__
_loaded = False


def _load_runtime(module):
    global _loaded
    if _loaded or getattr(module, "__name__", "") != "app":
        return
    try:
        import runtime_v2

        # The deployed Render service may still use `gunicorn app:app` instead
        # of render.yaml's stable entrypoint. Install the production CORS layer
        # here so every Vercel deployment URL can reach the API.
        from flask import request

        @module.app.after_request
        def allow_vercel_frontend(response):
            origin = request.headers.get("Origin")
            if origin and origin.startswith("https://") and origin.endswith(".vercel.app"):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Headers"] = (
                    "Content-Type, Authorization, X-Request-ID, X-Workspace-ID"
                )
                response.headers["Access-Control-Allow-Methods"] = (
                    "GET, POST, PUT, PATCH, DELETE, OPTIONS"
                )
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Vary"] = "Origin"
            return response

        _loaded = True
    except Exception:
        # Keep the base Flask app bootable if the optional runtime layer fails.
        pass


def _import(name, globals=None, locals=None, fromlist=(), level=0):
    module = _original_import(name, globals, locals, fromlist, level)
    if name == "app":
        _load_runtime(module)
    return module


builtins.__import__ = _import
