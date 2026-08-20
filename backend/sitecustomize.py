"""Load Nexora's stable runtime extensions after app.py is imported."""
import builtins

_original_import = builtins.__import__
_loaded = False


def _load_runtime(module):
    global _loaded
    if _loaded or getattr(module, "__name__", "") != "app":
        return
    try:
        import runtime_v2
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
