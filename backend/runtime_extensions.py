"""Runtime API extensions loaded once by gunicorn.

This module deliberately contains only routes that are not already defined in
app.py. It avoids importing the older app_extra module, which registered the
same Flask routes a second time and caused gunicorn workers to fail during
startup.
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

# Keep the existing API helpers, but make all existing workspace-scoped routes
# honor the workspace selected by the frontend through X-Workspace-ID.
_original_membership_for = app_module.membership_for


def selected_membership_for(user_id, workspace_id=None):
    if workspace_id is not None:
        return _original_membership_for(user_id, workspace_id)
    raw = request.headers.get("X-Workspace-ID")
    if raw:
        try:
            membership = _original_membership_for(user_id, int(raw))
            if membership:
                return membership
        except (TypeError, ValueError):
            pass
    # A newly accepted invitation becomes the most recent membership and is
    # therefore the default workspace when no explicit workspace is selected.
    return Membership.query.filter_by(user_id=user_id).order_by(Membership.created_at.desc()).first()


def selected_workspace_context(user_id=None):
    user_id = user_id or int(get_jwt_identity())
    membership = selected_membership_for(user_id)
    workspace = db.session.get(Workspace, membership.workspace_id) if membership else None
    return membership, workspace


app_module.membership_for = selected_membership_for
app_module.current_workspace_context = selected_workspace_context


def workspace_ids_for_user(user_id):
    return Membership.query.filter_by(user_id=user_id).order_by(Membership.created_at.asc()).all()


def migrate_legacy_projects(user_id, workspace_id):
    """Attach legacy projects owned by the user to their workspace, without deleting data."""
    projects = Project.query.filter_by(owner_id=user_id).all()
    changed = False
    for project in projects:
        link = ProjectWorkspace.query.filter_by(project_id=project.id).first()
        if not link:
            db.session.add(ProjectWorkspace(project_id=project.id, workspace_id=workspace_id))
            if not ProjectMember.query.filter_by(project_id=project.id, user_id=user_id).first():
                db.session.add(ProjectMember(project_id=project.id, user_id=user_id))
            changed = True
        if Task.query.filter_by(project_id=project.id).count():
            for task in Task.query.filter_by(project_id=project.id).all():
                if not TaskMeta.query.filter_by(task_id=task.id).first():
                    db.session.add(TaskMeta(task_id=task.id))
                    changed = True
    if changed:
        db.session.flush()


@app.get("/api/workspaces")
@jwt_required()
def runtime_list_workspaces():
    user_id = int(get_jwt_identity())
    memberships = workspace_ids_for_user(user_id)
    selected = selected_membership_for(user_id)
    return app_module.ok({
        "workspaces": [
            {
                "id": m.workspace_id,
                "name": db.session.get(Workspace, m.workspace_id).name,
                "slug": db.session.get(Workspace, m.workspace_id).slug,
                "role": m.role,
                "selected": bool(selected and selected.id == m.id),
            }
            for m in memberships
            if db.session.get(Workspace, m.workspace_id)
        ],
        "selectedWorkspaceId": selected.workspace_id if selected else None,
    })


@app.post("/api/workspaces/<int:workspace_id>/select")
@jwt_required()
def runtime_select_workspace(workspace_id):
    user_id = int(get_jwt_identity())
    membership = _original_membership_for(user_id, workspace_id)
    if not membership:
        return app_module.error("You are not a member of this workspace.", 403, "WORKSPACE_ACCESS_DENIED")
    workspace = db.session.get(Workspace, workspace_id)
    return app_module.ok({
        "workspace": {
            "id": workspace.id,
            "name": workspace.name,
            "slug": workspace.slug,
            "role": membership.role,
        }
    })


@app.get("/api/workspaces/current")
@jwt_required()
def runtime_current_workspace():
    user_id = int(get_jwt_identity())
    membership, workspace = selected_workspace_context(user_id)
    if not membership or not workspace:
        return app_module.error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")
    return app_module.ok({
        "workspace": {
            "id": workspace.id,
            "name": workspace.name,
            "slug": workspace.slug,
            "role": membership.role,
        }
    })


# Replace the original single-workspace response with the selected workspace.
app.view_functions["get_workspace"] = runtime_current_workspace


@app.post("/api/projects")
@jwt_required()
def runtime_create_project():
    user_id = int(get_jwt_identity())
    membership, workspace = selected_workspace_context(user_id)
    if not membership or membership.role not in {"Admin", "Manager"}:
        return app_module.error("You do not have permission to create projects.", 403, "FORBIDDEN")
    migrate_legacy_projects(user_id, workspace.id)
    data = request.get_json(silent=True) or {}
    name = app_module.clean_string(data.get("name"), 160)
    description = app_module.clean_string(data.get("description"), 2000)
    status = app_module.clean_string(data.get("status") or "Active", 40)
    if not name:
        return app_module.error("Project name is required.", 400, "VALIDATION_ERROR")
    if status not in app_module.PROJECT_STATUSES:
        return app_module.error("Invalid project status.", 400, "VALIDATION_ERROR")
    project = Project(name=name, description=description, status=status, owner_id=user_id)
    db.session.add(project)
    db.session.flush()
    db.session.add(ProjectWorkspace(project_id=project.id, workspace_id=workspace.id))
    db.session.add(ProjectMember(project_id=project.id, user_id=user_id))
    app_module.record_activity(user_id, "Created project", name)
    db.session.commit()
    return app_module.ok({"project": app_module.project_payload(project, workspace.id)}, 201)


@app.delete("/api/projects/<int:project_id>")
@jwt_required()
def runtime_delete_project(project_id):
    user_id = int(get_jwt_identity())
    membership, workspace = selected_workspace_context(user_id)
    if not membership or membership.role not in {"Admin", "Manager"}:
        return app_module.error("You do not have permission to delete projects.", 403, "FORBIDDEN")
    project = app_module.project_in_workspace(project_id, workspace.id) if workspace else None
    if not project:
        return app_module.error("Project not found.", 404, "PROJECT_NOT_FOUND")
    app_module.record_activity(user_id, "Deleted project", project.name)
    db.session.delete(project)
    db.session.commit()
    return app_module.ok({"message": "Project deleted."})


@app.post("/api/tasks")
@jwt_required()
def runtime_create_task():
    user_id = int(get_jwt_identity())
    membership, workspace = selected_workspace_context(user_id)
    if not membership or membership.role not in {"Admin", "Manager"}:
        return app_module.error("You do not have permission to create tasks.", 403, "FORBIDDEN")
    data = request.get_json(silent=True) or {}
    title = app_module.clean_string(data.get("title") or data.get("name"), 180)
    description = app_module.clean_string(data.get("description"), 4000)
    project_id = data.get("projectId") or data.get("project_id")
    assignee_id = data.get("assigneeId") or data.get("assignee_id")
    status = app_module.clean_string(data.get("status") or "Todo", 40)
    priority = app_module.clean_string(data.get("priority") or "Medium", 30)
    due_raw = app_module.clean_string(data.get("dueDate") or data.get("due_date"), 40) or None
    if not title or not project_id:
        return app_module.error("Task name and project are required.", 400, "VALIDATION_ERROR")
    try:
        project_id = int(project_id)
    except (TypeError, ValueError):
        return app_module.error("Invalid project.", 400, "VALIDATION_ERROR")
    if status not in app_module.TASK_STATUSES:
        return app_module.error("Invalid task status.", 400, "VALIDATION_ERROR")
    if priority not in app_module.TASK_PRIORITIES:
        return app_module.error("Invalid task priority.", 400, "VALIDATION_ERROR")
    project = app_module.project_in_workspace(project_id, workspace.id) if workspace else None
    if not project:
        return app_module.error("Project not found in this workspace.", 404, "PROJECT_NOT_FOUND")
    if assignee_id:
        try:
            assignee_id = int(assignee_id)
        except (TypeError, ValueError):
            return app_module.error("Invalid assignee.", 400, "VALIDATION_ERROR")
        if not Membership.query.filter_by(workspace_id=workspace.id, user_id=assignee_id).first():
            return app_module.error("Assignee must be a member of this workspace.", 400, "INVALID_ASSIGNEE")
    due_date = None
    if due_raw:
        try:
            due_date = datetime.fromisoformat(due_raw.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return app_module.error("Invalid due date.", 400, "VALIDATION_ERROR")
    task = Task(
        title=title,
        description=description,
        project_id=project.id,
        assignee_id=assignee_id,
        status=status,
        priority=priority,
    )
    db.session.add(task)
    db.session.flush()
    db.session.add(TaskMeta(task_id=task.id, due_date=due_date))
    app_module.refresh_project_progress(project.id)
    app_module.record_activity(user_id, "Created task", title)
    if assignee_id and assignee_id != user_id:
        app_module.notify(assignee_id, "Task assigned", f"You were assigned {title}.", "task")
    db.session.commit()
    return app_module.ok({"task": app_module.task_payload(task)}, 201)


@app.patch("/api/tasks/<int:task_id>")
@jwt_required()
def runtime_update_task(task_id):
    user_id = int(get_jwt_identity())
    membership, workspace = selected_workspace_context(user_id)
    task = app_module.task_in_workspace(task_id, workspace.id) if workspace else None
    if not task:
        return app_module.error("Task not found in this workspace.", 404, "TASK_NOT_FOUND")
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status is not None:
        new_status = app_module.clean_string(new_status, 40)
        if new_status not in app_module.TASK_STATUSES:
            return app_module.error("Invalid task status.", 400, "VALIDATION_ERROR")
        if membership.role not in {"Admin", "Manager"} and task.assignee_id != user_id:
            return app_module.error("You can only update tasks assigned to you.", 403, "FORBIDDEN")
        if new_status != task.status:
            old = task.status
            task.status = new_status
            app_module.record_activity(user_id, "Changed task status", f"{task.title}: {old} → {new_status}")
    for field in ("title", "description", "priority"):
        if field in data:
            max_len = 4000 if field == "description" else 180
            value = app_module.clean_string(data[field], max_len)
            if field == "priority" and value not in app_module.TASK_PRIORITIES:
                return app_module.error("Invalid task priority.", 400, "VALIDATION_ERROR")
            setattr(task, field, value)
    if "assigneeId" in data and membership.role in {"Admin", "Manager"}:
        aid = data.get("assigneeId")
        if aid:
            try:
                aid = int(aid)
            except (TypeError, ValueError):
                return app_module.error("Invalid assignee.", 400, "VALIDATION_ERROR")
            if not Membership.query.filter_by(workspace_id=workspace.id, user_id=aid).first():
                return app_module.error("Assignee must be a member of this workspace.", 400, "INVALID_ASSIGNEE")
        task.assignee_id = aid if aid else None
    if "dueDate" in data:
        meta = TaskMeta.query.filter_by(task_id=task.id).first()
        if not meta:
            meta = TaskMeta(task_id=task.id)
            db.session.add(meta)
        raw = data.get("dueDate")
        try:
            meta.due_date = datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None) if raw else None
        except (AttributeError, ValueError):
            return app_module.error("Invalid due date.", 400, "VALIDATION_ERROR")
    app_module.refresh_project_progress(task.project_id)
    db.session.commit()
    return app_module.ok({"task": app_module.task_payload(task)})


@app.delete("/api/tasks/<int:task_id>")
@jwt_required()
def runtime_delete_task(task_id):
    user_id = int(get_jwt_identity())
    membership, workspace = selected_workspace_context(user_id)
    if not membership or membership.role not in {"Admin", "Manager"}:
        return app_module.error("You do not have permission to delete tasks.", 403, "FORBIDDEN")
    task = app_module.task_in_workspace(task_id, workspace.id) if workspace else None
    if not task:
        return app_module.error("Task not found in this workspace.", 404, "TASK_NOT_FOUND")
    project_id = task.project_id
    app_module.record_activity(user_id, "Deleted task", task.title)
    db.session.delete(task)
    db.session.flush()
    app_module.refresh_project_progress(project_id)
    db.session.commit()
    return app_module.ok({"message": "Task deleted."})
