"""Workspace-aware runtime helpers.

The production entrypoint is stable_entrypoint.py. This module remains safe to
import directly so a Gunicorn configuration or local tooling cannot crash the
worker merely by importing it.
"""
from datetime import datetime
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
import app as app_module

app = app_module.app
db = app_module.db
User = app_module.User
Workspace = app_module.Workspace
Membership = app_module.Membership
Project = app_module.Project
ProjectWorkspace = app_module.ProjectWorkspace
ProjectMember = app_module.ProjectMember
Task = app_module.Task
TaskMeta = app_module.TaskMeta
Activity = app_module.Activity

# app.py may not expose membership_for until stable_entrypoint has initialized
# the workspace extension. Fall back to the original model query so importing
# this module can never prevent Gunicorn from booting.
def _base_membership_for(user_id, workspace_id=None):
    query = Membership.query.filter_by(user_id=user_id)
    if workspace_id is not None:
        return query.filter_by(workspace_id=workspace_id).first()
    return query.order_by(Membership.created_at.asc()).first()

original_membership_for = getattr(app_module, "membership_for", _base_membership_for)


def selected_membership(user_id):
    raw = request.headers.get("X-Workspace-ID")
    if raw:
        try:
            membership = original_membership_for(user_id, int(raw))
            if membership:
                return membership
        except (TypeError, ValueError):
            pass
    return Membership.query.filter_by(user_id=user_id).order_by(Membership.created_at.desc()).first()


def selected_context(user_id=None):
    user_id = user_id or int(get_jwt_identity())
    membership = selected_membership(user_id)
    workspace = db.session.get(Workspace, membership.workspace_id) if membership else None
    return membership, workspace


app_module.membership_for = lambda user_id, workspace_id=None: (
    original_membership_for(user_id, workspace_id)
    if workspace_id is not None else selected_membership(user_id)
)
app_module.current_workspace_context = selected_context


def legacy_migrate(user_id, workspace):
    if not workspace or workspace.owner_id != user_id:
        return
    changed = False
    for project in Project.query.filter_by(owner_id=user_id).all():
        link = ProjectWorkspace.query.filter_by(project_id=project.id).first()
        if not link:
            db.session.add(ProjectWorkspace(project_id=project.id, workspace_id=workspace.id))
            if not ProjectMember.query.filter_by(project_id=project.id, user_id=user_id).first():
                db.session.add(ProjectMember(project_id=project.id, user_id=user_id))
            changed = True
        for task in Task.query.filter_by(project_id=project.id).all():
            if not TaskMeta.query.filter_by(task_id=task.id).first():
                db.session.add(TaskMeta(task_id=task.id))
                changed = True
    if changed:
        db.session.flush()


def workspace_project_ids(workspace_id):
    return [x[0] for x in db.session.query(ProjectWorkspace.project_id).filter_by(workspace_id=workspace_id).all()]
