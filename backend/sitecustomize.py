"""Startup hook for the deployed Nexora API.

The API entrypoint is app.py. This hook deliberately does not import app.py
while Python is still importing sitecustomize, because that can create a
circular import in some serverless/runtime configurations. Instead it wraps
Python's import function and registers the Admin-only activity endpoint right
after app.py finishes loading.
"""

import builtins

_original_import = builtins.__import__
_registered = False


def _register_activity_delete(module):
    global _registered
    if _registered:
        return
    if not getattr(module, "__name__", "").split(".")[-1] == "app":
        return

    try:
        app = module.app
        if any(str(rule) == "/api/activity/<int:activity_id>" for rule in app.url_map.iter_rules()):
            _registered = True
            return

        from flask_jwt_extended import get_jwt_identity

        Activity = module.Activity
        Membership = module.Membership
        current_workspace_context = module.current_workspace_context
        db = module.db
        error = module.error
        ok = module.ok
        require_role = module.require_role

        @app.delete("/api/activity/<int:activity_id>")
        @require_role("Admin")
        def delete_activity(activity_id):
            user_id = int(get_jwt_identity())
            membership, workspace = current_workspace_context(user_id)
            if not membership or not workspace:
                return error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")

            activity = db.session.get(Activity, activity_id)
            if not activity:
                return error("Activity not found.", 404, "ACTIVITY_NOT_FOUND")

            # Activity is workspace-scoped through the user who created it.
            belongs_to_workspace = Membership.query.filter_by(
                workspace_id=workspace.id,
                user_id=activity.user_id,
            ).first()
            if not belongs_to_workspace:
                return error("Activity not found.", 404, "ACTIVITY_NOT_FOUND")

            db.session.delete(activity)
            db.session.commit()
            return ok({"message": "Activity deleted."})

        _registered = True
    except Exception:
        # Do not break API startup if the optional route cannot be registered.
        pass


def _import(name, globals=None, locals=None, fromlist=(), level=0):
    module = _original_import(name, globals, locals, fromlist, level)
    if name == "app" or (globals and globals.get("__package__") == "" and name.endswith("app")):
        _register_activity_delete(module)
    return module


builtins.__import__ = _import
