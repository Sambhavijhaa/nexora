from flask import g, request
from flask_jwt_extended import get_jwt_identity
from app import app, db, User, WorkspaceInvitation, error, ok, require_role, clean_string, EMAIL_RE, now_utc, record_activity, notify
from datetime import timedelta
import os
import uuid


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
