"""Stable workspace-scoped runtime routes.

Loaded after app.py has finished registering its normal routes. This module
reuses the existing models and helpers and replaces the workspace-sensitive
view functions so the selected X-Workspace-ID is authoritative.
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

original_membership_for = app_module.membership_for


def selected_membership(user_id):
    raw = request.headers.get("X-Workspace-ID")
    if raw:
        try:
            membership = original_membership_for(user_id, int(raw))
            if membership:
                return membership
        except (TypeError, ValueError):
            pass
    # If there is no selected workspace, prefer the newest membership. This is
    # important after accepting an invitation.
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
    # Only migrate truly legacy data into the user's own workspace. Never move
    # a user's old projects into somebody else's workspace.
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


def install_get(name, fn):
    app.view_functions[name] = fn


@app.get("/api/workspaces")
@jwt_required()
def list_workspaces():
    user_id = int(get_jwt_identity())
    memberships = Membership.query.filter_by(user_id=user_id).order_by(Membership.created_at.asc()).all()
    selected = selected_membership(user_id)
    result = []
    for membership in memberships:
        workspace = db.session.get(Workspace, membership.workspace_id)
        if workspace:
            result.append({
                "id": workspace.id,
                "name": workspace.name,
                "slug": workspace.slug,
                "role": membership.role,
                "selected": bool(selected and selected.id == membership.id),
            })
    return app_module.ok({
        "workspaces": result,
        "selectedWorkspaceId": selected.workspace_id if selected else None,
    })


@app.post("/api/workspaces/<int:workspace_id>/select")
@jwt_required()
def select_workspace(workspace_id):
    user_id = int(get_jwt_identity())
    membership = original_membership_for(user_id, workspace_id)
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
def current_workspace():
    membership, workspace = selected_context()
    if not membership or not workspace:
        return app_module.error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")
    return app_module.ok({"workspace": {
        "id": workspace.id,
        "name": workspace.name,
        "slug": workspace.slug,
        "role": membership.role,
    }})


@app.get("/api/workspace")
@jwt_required()
def get_selected_workspace():
    return current_workspace()


def get_team_runtime():
    user_id = int(get_jwt_identity())
    membership, workspace = selected_context(user_id)
    if not membership or not workspace:
        return app_module.error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")
    members = db.session.query(User, Membership).join(
        Membership, Membership.user_id == User.id
    ).filter(Membership.workspace_id == workspace.id).order_by(Membership.created_at.asc()).all()
    return app_module.ok({"members": [
        {**app_module.user_payload(user), "role": member.role,
         "joinedAt": member.created_at.isoformat() if member.created_at else None}
        for user, member in members
    ]})


def get_projects_runtime():
    user_id = int(get_jwt_identity())
    membership, workspace = selected_context(user_id)
    if not membership or not workspace:
        return app_module.error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")
    legacy_migrate(user_id, workspace)
    ids = workspace_project_ids(workspace.id)
    projects = Project.query.filter(Project.id.in_(ids)).order_by(Project.created_at.desc()).all() if ids else []
    db.session.commit()
    return app_module.ok({"projects": [app_module.project_payload(p, workspace.id) for p in projects]})


def get_tasks_runtime():
    user_id = int(get_jwt_identity())
    membership, workspace = selected_context(user_id)
    if not membership or not workspace:
        return app_module.error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")
    legacy_migrate(user_id, workspace)
    ids = workspace_project_ids(workspace.id)
    tasks = Task.query.filter(Task.project_id.in_(ids)).order_by(Task.created_at.desc()).all() if ids else []
    db.session.commit()
    return app_module.ok({"tasks": [app_module.task_payload(t) for t in tasks]})


def get_dashboard_runtime():
    user_id = int(get_jwt_identity())
    membership, workspace = selected_context(user_id)
    if not membership or not workspace:
        return app_module.error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")
    legacy_migrate(user_id, workspace)
    ids = workspace_project_ids(workspace.id)
    tasks = Task.query.filter(Task.project_id.in_(ids)).all() if ids else []
    projects = Project.query.filter(Project.id.in_(ids)).order_by(Project.created_at.desc()).all() if ids else []
    counts = {status: sum(task.status == status for task in tasks) for status in app_module.TASK_STATUSES}
    return app_module.ok({
        "stats": {
            "projects": len(projects),
            "tasks": len(tasks),
            "completed": counts["Done"],
            "teamMembers": Membership.query.filter_by(workspace_id=workspace.id).count(),
        },
        "taskBreakdown": {
            "done": counts["Done"], "inProgress": counts["In Progress"],
            "todo": counts["Todo"], "review": counts["Review"], "blocked": counts["Blocked"],
        },
        "projects": [app_module.project_payload(p, workspace.id) for p in projects[:6]],
        "activity": [],
    })


def get_analytics_runtime():
    membership, workspace = selected_context()
    if not membership or not workspace:
        return app_module.error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")
    ids = workspace_project_ids(workspace.id)
    tasks = Task.query.filter(Task.project_id.in_(ids)).all() if ids else []
    projects = Project.query.filter(Project.id.in_(ids)).all() if ids else []
    counts = {status: sum(task.status == status for task in tasks) for status in app_module.TASK_STATUSES}
    priorities = {priority: sum(task.priority == priority for task in tasks) for priority in app_module.TASK_PRIORITIES}
    total = len(tasks)
    return app_module.ok({
        "overview": {
            "completionRate": round(counts["Done"] / total * 100, 1) if total else 0,
            "totalTasks": total,
            "completedTasks": counts["Done"],
            "overdueTasks": 0,
            "activeProjects": sum(p.status == "Active" for p in projects),
            "teamMembers": Membership.query.filter_by(workspace_id=workspace.id).count(),
        },
        "tasksByStatus": counts,
        "tasksByPriority": priorities,
        "projectPerformance": [app_module.project_payload(p, workspace.id) for p in projects],
    })


def get_activity_runtime():
    membership, workspace = selected_context()
    if not membership or not workspace:
        return app_module.error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")
    activities = Activity.query.join(
        Membership, Membership.user_id == Activity.user_id
    ).filter(Membership.workspace_id == workspace.id).order_by(Activity.created_at.desc()).limit(100).all()
    return app_module.ok({"activity": [app_module.activity_payload(a) for a in activities]})


install_get("get_team", get_team_runtime)
install_get("get_projects", get_projects_runtime)
install_get("get_tasks", get_tasks_runtime)
install_get("dashboard_summary", get_dashboard_runtime)
install_get("analytics", get_analytics_runtime)
install_get("get_activity", get_activity_runtime)


@app.post("/api/projects")
@jwt_required()
def create_project_runtime():
    user_id = int(get_jwt_identity())
    membership, workspace = selected_context(user_id)
    if not membership or membership.role not in {"Admin", "Manager"}:
        return app_module.error("You do not have permission to create projects.", 403, "FORBIDDEN")
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


@app.post("/api/tasks")
@jwt_required()
def create_task_runtime():
    user_id = int(get_jwt_identity())
    membership, workspace = selected_context(user_id)
    if not membership or membership.role not in {"Admin", "Manager"}:
        return app_module.error("You do not have permission to create tasks.", 403, "FORBIDDEN")
    data = request.get_json(silent=True) or {}
    title = app_module.clean_string(data.get("title") or data.get("name"), 180)
    description = app_module.clean_string(data.get("description"), 4000)
    project_id = data.get("projectId") or data.get("project_id")
    assignee_id = data.get("assigneeId") or data.get("assignee_id")
    priority = app_module.clean_string(data.get("priority") or "Medium", 30)
    status = app_module.clean_string(data.get("status") or "Todo", 40)
    due_raw = app_module.clean_string(data.get("dueDate") or data.get("due_date"), 40) or None
    if not title or not project_id:
        return app_module.error("Task name and project are required.", 400, "VALIDATION_ERROR")
    try:
        project_id = int(project_id)
    except (TypeError, ValueError):
        return app_module.error("Invalid project.", 400, "VALIDATION_ERROR")
    if status not in app_module.TASK_STATUSES or priority not in app_module.TASK_PRIORITIES:
        return app_module.error("Invalid task status or priority.", 400, "VALIDATION_ERROR")
    project = app_module.project_in_workspace(project_id, workspace.id)
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
    task = Task(title=title, description=description, project_id=project.id,
                assignee_id=assignee_id, status=status, priority=priority)
    db.session.add(task)
    db.session.flush()
    db.session.add(TaskMeta(task_id=task.id, due_date=due_date))
    app_module.refresh_project_progress(project.id)
    app_module.record_activity(user_id, "Created task", title)
    if assignee_id and assignee_id != user_id:
        app_module.notify(assignee_id, "Task assigned", f"You were assigned {title}.", "task")
    db.session.commit()
    return app_module.ok({"task": app_module.task_payload(task)}, 201)


# Replace the existing route handlers by endpoint name. The URL rules remain
# unchanged, so the frontend contract does not change.
install_get("get_workspace", get_selected_workspace)
app.view_functions["create_project_runtime"] = create_project_runtime
app.view_functions["create_task_runtime"] = create_task_runtime

# Existing app.py does not define these endpoints, so the decorators above are
# the canonical POST routes. The PATCH/DELETE task/project routes are supplied
# by the previous runtime extension when present; their GET data is now fixed
# independently and remains backward compatible.
