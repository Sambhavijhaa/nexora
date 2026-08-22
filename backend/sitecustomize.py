"""Small compatibility layer loaded when Render runs gunicorn app:app.

Do not import the old workspace runtime here. The old runtime expects helper
functions that are no longer part of app.py and can silently prevent invitation
routes from being registered.
"""
import builtins
import os
import uuid
from datetime import timedelta

_original_import = builtins.__import__
_loaded = False


def _load_runtime(module):
    global _loaded
    if _loaded or getattr(module, "__name__", "") != "app":
        return
    try:
        from flask import g, request
        from flask_jwt_extended import get_jwt_identity, jwt_required

        app = module.app
        db = module.db
        User = module.User
        WorkspaceInvitation = module.WorkspaceInvitation
        Membership = module.Membership
        Workspace = module.Workspace
        Activity = module.Activity
        clean = module.clean
        EMAIL_RE = module.EMAIL_RE
        now_utc = module.now_utc
        error = module.error
        ok = module.ok
        ROLES = getattr(module, "ROLES", {"Admin", "Manager", "Member", "Viewer"})

        @app.after_request
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

        def selected_workspace(user_id):
            raw = request.headers.get("X-Workspace-ID") or request.args.get("workspaceId")
            try:
                workspace_id = int(raw) if raw else None
            except (TypeError, ValueError):
                workspace_id = None

            membership = None
            if workspace_id:
                membership = Membership.query.filter_by(
                    user_id=user_id, workspace_id=workspace_id
                ).first()
            if not membership:
                membership = Membership.query.filter_by(user_id=user_id).order_by(
                    Membership.created_at.asc()
                ).first()
            if not membership:
                return None, None
            return membership, db.session.get(Workspace, membership.workspace_id)

        # Render currently uses gunicorn app:app. Register the invitation-link
        # endpoint directly against that app so the Team page never depends on
        # the removed/renamed helper functions from the old runtime.
        if not any(str(rule) == "/api/team/invite-link" for rule in app.url_map.iter_rules()):
            @app.post("/api/team/invite-link")
            @jwt_required()
            def create_invitation_link_runtime():
                user_id = int(get_jwt_identity())
                membership, workspace = selected_workspace(user_id)
                if not membership or not workspace:
                    return error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")
                if membership.role not in {"Admin", "Manager"}:
                    return error("You do not have permission to invite members.", 403, "FORBIDDEN")

                data = request.get_json(silent=True) or {}
                email = clean(data.get("email"), 255).lower()
                role = clean(data.get("role") or "Member", 40)
                if not EMAIL_RE.match(email):
                    return error("Enter a valid email address.", 400, "VALIDATION_ERROR")
                if role not in ROLES:
                    return error("Invalid workspace role.", 400, "VALIDATION_ERROR")

                try:
                    invitation = WorkspaceInvitation.query.filter_by(
                        workspace_id=workspace.id,
                        email=email,
                        accepted_at=None,
                    ).order_by(WorkspaceInvitation.created_at.desc()).first()

                    if invitation and invitation.expires_at > now_utc():
                        invitation.role = role
                    else:
                        invitation = WorkspaceInvitation(
                            workspace_id=workspace.id,
                            email=email,
                            role=role,
                            token=uuid.uuid4().hex + uuid.uuid4().hex,
                            expires_at=now_utc() + timedelta(days=7),
                        )
                        db.session.add(invitation)
                        db.session.flush()

                    # Record the invitation without relying on the old
                    # record_activity/notify helpers that caused startup failures.
                    db.session.add(Activity(
                        user_id=user_id,
                        action="Invited a workspace member",
                        context=email,
                    ))
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
                except Exception:
                    db.session.rollback()
                    module.logger.exception("Failed to create workspace invitation")
                    return error("Could not create the invitation right now.", 500, "INVITATION_CREATE_FAILED")

        _loaded = True
    except Exception:
        # Never make Gunicorn fail just because this optional compatibility
        # layer could not load.
        pass


def _import(name, globals=None, locals=None, fromlist=(), level=0):
    module = _original_import(name, globals, locals, fromlist, level)
    if name == "app":
        _load_runtime(module)
    return module


builtins.__import__ = _import
