from flask import g, request
from flask_jwt_extended import get_jwt_identity, create_access_token, jwt_required
from app import app, db, User, Workspace, Membership, WorkspaceInvitation, Project, ProjectWorkspace, ProjectMember, Task, TaskMeta, error, ok, clean, EMAIL_RE, now_utc, record_activity, notify, token_response, validate_password, slugify, project_payload, task_payload, TASK_STATUSES, TASK_PRIORITIES
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
import os
import uuid

ALLOWED_ROLES = {"Admin", "Manager", "Member", "Viewer"}

@app.after_request
def ensure_frontend_cors(response):
    origin = request.headers.get("Origin")
    allowed = {"https://nexora-ops.vercel.app", "https://nexora.vercel.app"}
    if origin in allowed or (origin and origin.endswith(".vercel.app")):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Request-ID, X-Workspace-ID"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Vary"] = "Origin"
    return response

def current_user():
    return db.session.get(User, int(get_jwt_identity()))

def migrate_legacy_data(user, workspace):
    """Attach old projects to the user's first workspace without deleting old data."""
    changed = False
    owned_projects = Project.query.filter_by(owner_id=user.id).all()
    for project in owned_projects:
        link = ProjectWorkspace.query.filter_by(project_id=project.id).first()
        if not link:
            db.session.add(ProjectWorkspace(project_id=project.id, workspace_id=workspace.id))
            changed = True
        elif link.workspace_id == workspace.id and not ProjectMember.query.filter_by(project_id=project.id, user_id=user.id).first():
            db.session.add(ProjectMember(project_id=project.id, user_id=user.id))
            changed = True
        for task in Task.query.filter_by(project_id=project.id).all():
            if not TaskMeta.query.filter_by(task_id=task.id).first():
                db.session.add(TaskMeta(task_id=task.id))
                changed = True
    if changed:
        db.session.flush()

def ensure_workspace_for_user(user):
    membership = Membership.query.filter_by(user_id=user.id).order_by(Membership.created_at.asc()).first()
    if membership:
        workspace = db.session.get(Workspace, membership.workspace_id)
        migrate_legacy_data(user, workspace)
        return workspace
    workspace = Workspace(name=f"{user.name}'s Workspace", slug=slugify(f"{user.name}-workspace"), owner_id=user.id)
    db.session.add(workspace)
    db.session.flush()
    db.session.add(Membership(workspace_id=workspace.id, user_id=user.id, role="Admin"))
    migrate_legacy_data(user, workspace)
    return workspace

def selected_membership(user_id):
    workspace_id = request.headers.get("X-Workspace-ID")
    if workspace_id:
        try:
            workspace_id = int(workspace_id)
        except ValueError:
            workspace_id = None
    query = Membership.query.filter_by(user_id=user_id)
    if workspace_id:
        membership = query.filter_by(workspace_id=workspace_id).first()
        if membership:
            return membership
    return query.order_by(Membership.created_at.asc()).first()

def selected_workspace(user_id):
    membership = selected_membership(user_id)
    return (membership, db.session.get(Workspace, membership.workspace_id)) if membership else (None, None)

def workspace_project_ids(workspace_id):
    return [x[0] for x in db.session.query(ProjectWorkspace.project_id).filter_by(workspace_id=workspace_id).all()]

def workspace_user(user_id, workspace_id):
    return Membership.query.filter_by(user_id=user_id, workspace_id=workspace_id).first()
