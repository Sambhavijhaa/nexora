import app_extra
from app import app, db, Membership, Workspace
from flask_jwt_extended import get_jwt_identity
from flask import request


def preferred_membership(user_id):
    workspace_id = request.headers.get("X-Workspace-ID")
    if workspace_id:
        try:
            workspace_id = int(workspace_id)
        except ValueError:
            workspace_id = None
    query = Membership.query.filter_by(user_id=user_id)
    if workspace_id:
        selected = query.filter_by(workspace_id=workspace_id).first()
        if selected:
            return selected
    # If no explicit workspace has been selected, use the newest membership.
    # This makes a newly accepted invitation immediately become the active workspace.
    return query.order_by(Membership.created_at.desc()).first()


def preferred_workspace(user_id):
    membership = preferred_membership(user_id)
    return (membership, db.session.get(Workspace, membership.workspace_id)) if membership else (None, None)

app_extra.selected_membership = preferred_membership
app_extra.selected_workspace = preferred_workspace
app.view_functions["get_workspace"] = app_extra.get_selected_workspace_extra
app.view_functions["get_team"] = app_extra.get_team_extra
app.view_functions["get_projects"] = app_extra.get_projects_extra
app.view_functions["get_tasks"] = app_extra.get_tasks_extra
app.view_functions["dashboard_summary"] = app_extra.dashboard_summary_extra
app.view_functions["analytics"] = app_extra.analytics_extra
app.view_functions["get_activity"] = app_extra.activity_extra
