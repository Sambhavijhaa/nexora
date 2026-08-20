import app as app_module
from flask import request, g
from flask_jwt_extended import get_jwt_identity, jwt_required

# Use the most recently joined workspace by default. A workspace ID can still be
# explicitly selected later with X-Workspace-ID.
_original_membership_for = app_module.membership_for

def selected_membership_for(user_id, workspace_id=None):
    requested = request.headers.get("X-Workspace-ID") if request else None
    if workspace_id:
        return _original_membership_for(user_id, workspace_id)
    if requested:
        try:
            membership = _original_membership_for(user_id, int(requested))
            if membership:
                return membership
        except (TypeError, ValueError):
            pass
    return app_module.Membership.query.filter_by(user_id=user_id).order_by(app_module.Membership.created_at.desc()).first()

app_module.membership_for = selected_membership_for

def selected_workspace_context(user_id=None):
    user_id = user_id or int(get_jwt_identity())
    membership = selected_membership_for(user_id)
    workspace = app_module.Workspace.query.get(membership.workspace_id) if membership else None
    return membership, workspace

app_module.current_workspace_context = selected_workspace_context

@app_module.app.get("/api/workspaces")
@jwt_required()
def list_workspaces_extra():
    user_id = int(get_jwt_identity())
    rows = app_module.Membership.query.filter_by(user_id=user_id).order_by(app_module.Membership.created_at.desc()).all()
    selected = selected_membership_for(user_id)
    return app_module.ok({"workspaces": [
        {
            "id": m.workspace_id,
            "name": app_module.Workspace.query.get(m.workspace_id).name,
            "role": m.role,
            "selected": bool(selected and selected.id == m.id),
        }
        for m in rows
        if app_module.Workspace.query.get(m.workspace_id)
    ]})

@app_module.app.post("/api/workspaces/select")
@jwt_required()
def select_workspace_extra():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    try:
        workspace_id = int(data.get("workspaceId"))
    except (TypeError, ValueError):
        return app_module.error("A valid workspace is required.", 400, "VALIDATION_ERROR")
    membership = _original_membership_for(user_id, workspace_id)
    if not membership:
        return app_module.error("You are not a member of this workspace.", 403, "WORKSPACE_ACCESS_DENIED")
    workspace = app_module.Workspace.query.get(workspace_id)
    return app_module.ok({"workspace": {"id": workspace.id, "name": workspace.name, "slug": workspace.slug, "role": membership.role}})
