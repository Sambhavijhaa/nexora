"""Nexora deployment compatibility routes loaded automatically by Python."""
import builtins
import os
import uuid
from datetime import timedelta

_original_import = builtins.__import__
_registered = False


def _register_routes(module):
    global _registered
    if _registered or getattr(module, "__name__", "").split(".")[-1] != "app":
        return
    try:
        app = module.app
        from flask import g, request
        from flask_jwt_extended import get_jwt_identity
        Activity = module.Activity
        Membership = module.Membership
        WorkspaceInvitation = module.WorkspaceInvitation
        User = module.User
        db = module.db
        error = module.error
        ok = module.ok
        require_role = module.require_role
        clean_string = module.clean_string
        EMAIL_RE = module.EMAIL_RE
        now_utc = module.now_utc
        record_activity = module.record_activity
        notify = module.notify

        # Keep the workspace chosen by an invitation as the user's active workspace.
        def latest_workspace_for_user(user_id):
            membership = Membership.query.filter_by(user_id=user_id).order_by(Membership.created_at.desc()).first()
            return module.Workspace.query.get(membership.workspace_id) if membership else None
        module.workspace_for_user = latest_workspace_for_user

        if not any(str(rule) == "/api/activity/<int:activity_id>" for rule in app.url_map.iter_rules()):
            @app.delete("/api/activity/<int:activity_id>")
            @require_role("Admin")
            def delete_activity(activity_id):
                user_id = int(get_jwt_identity())
                membership, workspace = module.current_workspace_context(user_id)
                if not membership or not workspace:
                    return error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")
                activity = db.session.get(Activity, activity_id)
                if not activity or not Membership.query.filter_by(workspace_id=workspace.id, user_id=activity.user_id).first():
                    return error("Activity not found.", 404, "ACTIVITY_NOT_FOUND")
                db.session.delete(activity)
                db.session.commit()
                return ok({"message": "Activity deleted."})

        # This endpoint performs invitation creation and link generation in ONE transaction.
        # It avoids the old two-request flow that could report "Could not create invitation"
        # even after the database row had been created.
        if not any(str(rule) == "/api/team/invite-link" for rule in app.url_map.iter_rules()):
            @app.post("/api/team/invite-link")
            @require_role("Admin", "Manager")
            def create_invitation_link():
                data = request.get_json(silent=True) or {}
                email = clean_string(data.get("email"), 255).lower()
                role = clean_string(data.get("role") or "Member", 40)
                if not EMAIL_RE.match(email) or role not in {"Admin", "Manager", "Member", "Viewer"}:
                    return error("A valid email and role are required.", 400, "VALIDATION_ERROR")

                invitation = WorkspaceInvitation.query.filter_by(
                    workspace_id=g.workspace.id,
                    email=email,
                    accepted_at=None,
                ).order_by(WorkspaceInvitation.created_at.desc()).first()

                if invitation and invitation.expires_at > now_utc():
                    invitation.role = role
                else:
                    invitation = WorkspaceInvitation(
                        workspace_id=g.workspace.id,
                        email=email,
                        role=role,
                        token=uuid.uuid4().hex + uuid.uuid4().hex,
                        expires_at=now_utc() + timedelta(days=7),
                    )
                    db.session.add(invitation)
                    db.session.flush()

                existing_user = User.query.filter(User.email.ilike(email)).first()
                if existing_user:
                    notify(existing_user.id, "Workspace invitation", f"You have been invited to {g.workspace.name} as {role}.", "invite")
                record_activity(int(get_jwt_identity()), "Invited a workspace member", email)
                db.session.commit()

                base = os.getenv("FRONTEND_URL", "https://nexora-ops.vercel.app").rstrip("/")
                return ok({
                    "invitation": {
                        "id": invitation.id,
                        "email": invitation.email,
                        "role": invitation.role,
                        "expiresAt": invitation.expires_at.isoformat(),
                    },
                    "invitationLink": f"{base}/invite/{invitation.token}",
                }, 201)

        _registered = True
    except Exception:
        # Never prevent Gunicorn from loading the main app if this compatibility layer fails.
        pass


def _import(name, globals=None, locals=None, fromlist=(), level=0):
    module = _original_import(name, globals, locals, fromlist, level)
    if name == "app" or (globals and globals.get("__package__") == "" and name.endswith("app")):
        _register_routes(module)
    return module

builtins.__import__ = _import
