from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import app
import app as app_module
import app_extra

# Use the stable workspace-aware runtime instead of importing runtime_v2 during boot.
app_module.membership_for = lambda user_id, workspace_id=None: (
    app_extra.workspace_user(user_id, workspace_id)
    if workspace_id is not None
    else app_extra.selected_membership(user_id)
)
app_module.current_workspace_context = app_extra.selected_workspace

for endpoint, handler in {
    "get_workspace": app_extra.get_selected_workspace_extra,
    "get_team": app_extra.get_team_extra,
    "get_projects": app_extra.get_projects_extra,
    "get_tasks": app_extra.get_tasks_extra,
}.items():
    app.view_functions[endpoint] = handler

@app.post("/api/team/accept-stable")
@jwt_required()
def accept_invitation_stable():
    token = app_extra.clean((request.get_json(silent=True) or {}).get("token"), 128)
    invitation = app_extra.WorkspaceInvitation.query.filter_by(token=token).first()
    if not invitation or invitation.accepted_at or invitation.expires_at < app_extra.now_utc():
        return app_extra.error("This invitation is invalid or expired.", 400, "INVITATION_INVALID")
    user = app_extra.db.session.get(app_extra.User, int(get_jwt_identity()))
    if user.email.lower() != invitation.email.lower():
        return app_extra.error("This invitation was sent to a different email address.", 403, "INVITATION_EMAIL_MISMATCH")
    membership = app_extra.Membership.query.filter_by(workspace_id=invitation.workspace_id, user_id=user.id).first()
    if not membership:
        membership = app_extra.Membership(workspace_id=invitation.workspace_id, user_id=user.id, role=invitation.role)
        app_extra.db.session.add(membership)
    invitation.accepted_at = app_extra.now_utc()
    app_extra.record_activity(user.id, "Joined the workspace", str(invitation.workspace_id))
    app_extra.db.session.commit()
    workspace = app_extra.db.session.get(app_extra.Workspace, invitation.workspace_id)
    return app_extra.ok({"message": "Invitation accepted.", "workspace": {
        "id": workspace.id,
        "name": workspace.name,
        "slug": workspace.slug,
        "role": membership.role,
    }})

app.view_functions["accept_invitation"] = accept_invitation_stable
