"""Small production-safe workspace/activity runtime patch for Nexora.

Keeps the main Flask app intact while adding true workspace-scoped activity
and recording activity for the existing project/task mutations.
"""
from flask import request, make_response
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import text

import app as app_module

app = app_module.app
db = app_module.db
Activity = app_module.Activity
Membership = app_module.Membership
Workspace = app_module.Workspace
User = app_module.User


def selected_workspace(user_id):
    raw = request.headers.get("X-Workspace-ID") or request.args.get("workspaceId")
    try:
        workspace_id = int(raw) if raw else None
    except (TypeError, ValueError):
        workspace_id = None
    if workspace_id:
        membership = Membership.query.filter_by(user_id=user_id, workspace_id=workspace_id).first()
        if membership:
            return membership, db.session.get(Workspace, workspace_id)
    membership = Membership.query.filter_by(user_id=user_id).order_by(Membership.created_at.asc()).first()
    return ((membership, db.session.get(Workspace, membership.workspace_id)) if membership else (None, None))


def ensure_activity_workspace_column():
    """Add workspace tracking without resetting or deleting existing data."""
    engine = db.engine
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(text("ALTER TABLE activity ADD COLUMN IF NOT EXISTS workspace_id INTEGER"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_activity_workspace_id ON activity (workspace_id)"))
        elif dialect == "sqlite":
            columns = conn.execute(text("PRAGMA table_info(activity)")).fetchall()
            if not any(row[1] == "workspace_id" for row in columns):
                conn.execute(text("ALTER TABLE activity ADD COLUMN workspace_id INTEGER"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_activity_workspace_id ON activity (workspace_id)"))
        else:
            try:
                conn.execute(text("ALTER TABLE activity ADD COLUMN workspace_id INTEGER"))
            except Exception:
                pass
        conn.execute(text(
            "UPDATE activity SET workspace_id = "
            "(SELECT MIN(workspace_memberships.workspace_id) FROM workspace_memberships "
            "WHERE workspace_memberships.user_id = activity.user_id) "
            "WHERE workspace_id IS NULL"
        ))


@jwt_required()
def workspace_activity():
    user_id = int(get_jwt_identity())
    membership, workspace = selected_workspace(user_id)
    if not membership or not workspace:
        return app_module.error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")
    rows = db.session.query(Activity, User).join(User, User.id == Activity.user_id).filter(
        text("activity.workspace_id = :workspace_id")
    ).params(workspace_id=workspace.id).order_by(Activity.created_at.desc()).limit(100).all()
    return app_module.ok({"activity":[
        {
            "id": activity.id,
            "action": activity.action,
            "context": activity.context or "",
            "user": app_module.user_payload(user),
            "createdAt": activity.created_at.isoformat() if activity.created_at else None,
        }
        for activity, user in rows
    ]})


@jwt_required()
def delete_workspace_activity(aid):
    user_id = int(get_jwt_identity())
    membership, workspace = selected_workspace(user_id)
    if not membership or membership.role != "Admin":
        return app_module.error("You do not have permission to delete activity.", 403, "FORBIDDEN")
    activity = db.session.query(Activity).filter(
        Activity.id == aid,
        text("activity.workspace_id = :workspace_id")
    ).params(workspace_id=workspace.id).first()
    if not activity:
        return app_module.error("Activity not found.", 404, "ACTIVITY_NOT_FOUND")
    db.session.delete(activity)
    db.session.commit()
    return app_module.ok({"message":"Activity deleted."})


def select_workspace(workspace_id):
    user_id = int(get_jwt_identity())
    membership = Membership.query.filter_by(user_id=user_id, workspace_id=workspace_id).first()
    if not membership:
        return app_module.error("You are not a member of this workspace.", 403, "WORKSPACE_ACCESS_DENIED")
    workspace = db.session.get(Workspace, workspace_id)
    return app_module.ok({"workspace":{
        "id":workspace.id,"name":workspace.name,"slug":workspace.slug,"role":membership.role
    }})


def record_after(endpoint_name, action, context_getter):
    original = app.view_functions.get(endpoint_name)
    if not original or getattr(original, "_workspace_activity_wrapped", False):
        return
    def wrapped(*args, **kwargs):
        result = original(*args, **kwargs)
        response = make_response(result)
        if 200 <= response.status_code < 300:
            try:
                user_id = int(get_jwt_identity())
                membership, workspace = selected_workspace(user_id)
                if membership and workspace:
                    context = context_getter(response)
                    db.session.execute(text(
                        "INSERT INTO activity (user_id, workspace_id, action, context) "
                        "VALUES (:user_id, :workspace_id, :action, :context)"
                    ), {
                        "user_id":user_id,
                        "workspace_id":workspace.id,
                        "action":action,
                        "context":(context or "")[:180],
                    })
                    db.session.commit()
            except Exception:
                db.session.rollback()
                app.logger.exception("Could not record workspace activity")
        return response
    wrapped._workspace_activity_wrapped = True
    app.view_functions[endpoint_name] = wrapped


ensure_activity_workspace_column()
app.view_functions["activity"] = workspace_activity
app.view_functions["delete_activity"] = delete_workspace_activity

# Selection remains client-side through X-Workspace-ID; this only validates access.
if "select_workspace" not in app.view_functions:
    app.add_url_rule(
        "/api/workspaces/<int:workspace_id>/select",
        endpoint="select_workspace",
        view_func=jwt_required()(select_workspace),
        methods=["POST"],
    )

record_after("create_project","Created project",lambda response: ((response.get_json() or {}).get("project") or {}).get("name", ""))
record_after("create_task","Created task",lambda response: ((response.get_json() or {}).get("task") or {}).get("title", ""))
record_after("update_task","Updated task",lambda response: "Task updated")
record_after("delete_project","Deleted project",lambda response: "Project deleted")
record_after("delete_task","Deleted task",lambda response: "Task deleted")
