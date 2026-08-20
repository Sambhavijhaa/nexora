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
        from flask_jwt_extended import get_jwt_identity, create_access_token, create_refresh_token, jwt_required
        Activity = module.Activity
        Membership = module.Membership
        WorkspaceInvitation = module.WorkspaceInvitation
        Workspace = module.Workspace
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
        token_response = module.token_response
        validate_password = module.validate_password
        slugify = module.slugify
        from werkzeug.security import check_password_hash, generate_password_hash

        # Keep the workspace chosen by an invitation as the user's active workspace.
        def latest_workspace_for_user(user_id):
            membership = Membership.query.filter_by(user_id=user_id).order_by(Membership.created_at.desc()).first()
            return Workspace.query.get(membership.workspace_id) if membership else None
        module.workspace_for_user = latest_workspace_for_user

        # Authentication routes must exist even when Render starts the service with
        # the older `gunicorn app:app` command instead of app_extra:app.
        if not any(str(rule) == "/api/auth/register" for rule in app.url_map.iter_rules()):
            @app.post("/api/auth/register")
            def register_compat():
                data = request.get_json(silent=True) or {}
                name = clean_string(data.get("name"), 100)
                email = clean_string(data.get("email"), 255).lower()
                password = str(data.get("password") or "")
                if not name or not EMAIL_RE.match(email):
                    return error("Name and a valid email are required.", 400, "VALIDATION_ERROR")
                password_error = validate_password(password)
                if password_error:
                    return error(password_error, 400, "VALIDATION_ERROR")
                if User.query.filter(User.email.ilike(email)).first():
                    return error("An account with this email already exists.", 409, "EMAIL_EXISTS")
                user = User(name=name, email=email, password_hash=generate_password_hash(password), role="Admin")
                db.session.add(user)
                db.session.flush()
                workspace = Workspace(name=f"{name}'s Workspace", slug=slugify(f"{name}-workspace"), owner_id=user.id)
                db.session.add(workspace)
                db.session.flush()
                db.session.add(Membership(workspace_id=workspace.id, user_id=user.id, role="Admin"))
                db.session.commit()
                return ok(token_response(user), 201)

        if not any(str(rule) == "/api/auth/login" for rule in app.url_map.iter_rules()):
            @app.post("/api/auth/login")
            def login_compat():
                data = request.get_json(silent=True) or {}
                email = clean_string(data.get("email"), 255).lower()
                password = str(data.get("password") or "")
                user = User.query.filter(User.email.ilike(email)).first()
                if not user or not check_password_hash(user.password_hash, password):
                    return error("Invalid email or password.", 401, "INVALID_CREDENTIALS")
                return ok(token_response(user))

        if not any(str(rule) == "/api/auth/refresh" for rule in app.url_map.iter_rules()):
            @app.post("/api/auth/refresh")
            @jwt_required(refresh=True)
            def refresh_compat():
                user = db.session.get(User, int(get_jwt_identity()))
                if not user:
                    return error("User account not found.", 401, "AUTH_INVALID")
                return ok({"accessToken": create_access_token(identity=str(user.id))})

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
                    workspace_id=g.workspace.id, email=email, accepted_at=None
                ).order_by(WorkspaceInvitation.created_at.desc()).first()
                if invitation and invitation.expires_at > now_utc():
                    invitation.role = role
                else:
                    invitation = WorkspaceInvitation(
                        workspace_id=g.workspace.id, email=email, role=role,
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
                    "invitation": {"id": invitation.id, "email": invitation.email, "role": invitation.role, "expiresAt": invitation.expires_at.isoformat()},
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
