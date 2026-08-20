"""Optional startup routes for the deployed Nexora API."""
import builtins

_original_import = builtins.__import__
_registered = False


def _register_routes(module):
    global _registered
    if _registered or getattr(module, "__name__", "").split(".")[-1] != "app":
        return
    try:
        app = module.app
        from flask import g
        from flask_jwt_extended import get_jwt_identity
        Activity = module.Activity
        Membership = module.Membership
        WorkspaceInvitation = module.WorkspaceInvitation
        current_workspace_context = module.current_workspace_context
        db = module.db
        error = module.error
        ok = module.ok
        require_role = module.require_role
        import os

        if not any(str(rule) == "/api/activity/<int:activity_id>" for rule in app.url_map.iter_rules()):
            @app.delete("/api/activity/<int:activity_id>")
            @require_role("Admin")
            def delete_activity(activity_id):
                user_id = int(get_jwt_identity())
                membership, workspace = current_workspace_context(user_id)
                if not membership or not workspace:
                    return error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")
                activity = db.session.get(Activity, activity_id)
                if not activity or not Membership.query.filter_by(workspace_id=workspace.id, user_id=activity.user_id).first():
                    return error("Activity not found.", 404, "ACTIVITY_NOT_FOUND")
                db.session.delete(activity)
                db.session.commit()
                return ok({"message": "Activity deleted."})

        if not any(str(rule) == "/api/team/invite/<int:invitation_id>/link" for rule in app.url_map.iter_rules()):
            @app.get("/api/team/invite/<int:invitation_id>/link")
            @require_role("Admin", "Manager")
            def get_invitation_link(invitation_id):
                invitation = WorkspaceInvitation.query.filter_by(id=invitation_id, workspace_id=g.workspace.id).first()
                if not invitation:
                    return error("Invitation not found.", 404, "INVITATION_NOT_FOUND")
                base = os.getenv("FRONTEND_URL", "https://nexora-ops.vercel.app").rstrip("/")
                return ok({"invitationLink": f"{base}/invite/{invitation.token}", "invitation": {"id": invitation.id, "email": invitation.email, "role": invitation.role, "expiresAt": invitation.expires_at.isoformat()}})

        _registered = True
    except Exception:
        pass


def _import(name, globals=None, locals=None, fromlist=(), level=0):
    module = _original_import(name, globals, locals, fromlist, level)
    if name == "app" or (globals and globals.get("__package__") == "" and name.endswith("app")):
        _register_routes(module)
    return module

builtins.__import__ = _import
