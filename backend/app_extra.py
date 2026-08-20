from flask import g, request
from flask_jwt_extended import get_jwt_identity, create_access_token, jwt_required
from app import app, db, User, Workspace, Membership, WorkspaceInvitation, Project, ProjectWorkspace, ProjectMember, Task, TaskMeta, error, ok, clean_string, EMAIL_RE, now_utc, record_activity, notify, token_response, validate_password, slugify, project_payload, task_payload, TASK_STATUSES, TASK_PRIORITIES
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
import os
import uuid

ALLOWED_ROLES = {"Admin", "Manager", "Member", "Viewer"}

@app.after_request
def ensure_frontend_cors(response):
    origin = request.headers.get("Origin")
    allowed = {"https://nexora-ops.vercel.app", "https://nexora.vercel.app"}
    if origin in allowed:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Request-ID, X-Workspace-ID"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Vary"] = "Origin"
    return response

def current_user():
    return db.session.get(User, int(get_jwt_identity()))

def migrate_legacy_data(user, workspace):
    """Attach old projects to the user's first workspace without deleting or rewriting old data."""
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

@app.get("/api/workspaces")
@jwt_required()
def list_workspaces_extra():
    user = current_user()
    first = ensure_workspace_for_user(user)
    db.session.commit()
    membership, _ = selected_workspace(user.id)
    memberships = Membership.query.filter_by(user_id=user.id).order_by(Membership.created_at.asc()).all()
    workspaces = []
    for m in memberships:
        w = db.session.get(Workspace, m.workspace_id)
        if w:
            workspaces.append({"id": w.id, "name": w.name, "slug": w.slug, "role": m.role, "selected": bool(membership and m.id == membership.id)})
    return ok({"workspaces": workspaces, "selectedWorkspaceId": membership.workspace_id if membership else first.id})

@app.get("/api/workspace")
@jwt_required()
def get_selected_workspace_extra():
    user = current_user()
    ensure_workspace_for_user(user)
    membership, workspace = selected_workspace(user.id)
    db.session.commit()
    if not membership or not workspace:
        return error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")
    return ok({"workspace": {"id": workspace.id, "name": workspace.name, "slug": workspace.slug, "role": membership.role}})

@app.post("/api/workspaces/<int:workspace_id>/select")
@jwt_required()
def select_workspace_extra(workspace_id):
    user_id = int(get_jwt_identity())
    membership = workspace_user(user_id, workspace_id)
    if not membership:
        return error("You are not a member of this workspace.", 403, "WORKSPACE_ACCESS_DENIED")
    workspace = db.session.get(Workspace, workspace_id)
    return ok({"workspace": {"id": workspace.id, "name": workspace.name, "slug": workspace.slug, "role": membership.role}})

@app.get("/api/team")
@jwt_required()
def get_team_extra():
    user_id = int(get_jwt_identity())
    user = current_user()
    workspace = ensure_workspace_for_user(user)
    membership, workspace = selected_workspace(user_id)
    if not membership or not workspace:
        return error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")
    members = db.session.query(User, Membership).join(Membership, Membership.user_id == User.id).filter(Membership.workspace_id == workspace.id).order_by(Membership.created_at.asc()).all()
    return ok({"members": [{**{k: v for k, v in {"id": u.id, "name": u.name, "email": u.email, "role": m.role}.items()}, "joinedAt": m.created_at.isoformat() if m.created_at else None} for u, m in members]})

@app.get("/api/projects")
@jwt_required()
def get_projects_extra():
    user = current_user(); ensure_workspace_for_user(user)
    membership, workspace = selected_workspace(user.id)
    ids = workspace_project_ids(workspace.id) if workspace else []
    projects = Project.query.filter(Project.id.in_(ids)).order_by(Project.created_at.desc()).all() if ids else []
    for p in projects:
        migrate_legacy_data(user, workspace)
    db.session.commit()
    return ok({"projects": [project_payload(p, workspace.id) for p in projects]})

@app.get("/api/tasks")
@jwt_required()
def get_tasks_extra():
    user = current_user(); ensure_workspace_for_user(user)
    membership, workspace = selected_workspace(user.id)
    ids = workspace_project_ids(workspace.id) if workspace else []
    tasks = Task.query.filter(Task.project_id.in_(ids)).order_by(Task.created_at.desc()).all() if ids else []
    for t in tasks:
        if not TaskMeta.query.filter_by(task_id=t.id).first():
            db.session.add(TaskMeta(task_id=t.id))
    db.session.commit()
    return ok({"tasks": [task_payload(t) for t in tasks]})

@app.post("/api/projects")
@jwt_required()
def create_project_extra():
    user_id = int(get_jwt_identity())
    user = current_user()
    membership, workspace = selected_workspace(user_id)
    if not membership or membership.role not in {"Admin", "Manager"}:
        return error("You do not have permission to create projects.", 403, "FORBIDDEN")
    data = request.get_json(silent=True) or {}
    name = clean_string(data.get("name"), 160)
    description = clean_string(data.get("description"), 2000)
    status = clean_string(data.get("status") or "Active", 40)
    if not name:
        return error("Project name is required.", 400, "VALIDATION_ERROR")
    if status not in {"Active", "On Hold", "Completed", "Archived"}:
        return error("Invalid project status.", 400, "VALIDATION_ERROR")
    project = Project(name=name, description=description, status=status, owner_id=user_id)
    db.session.add(project); db.session.flush()
    db.session.add(ProjectWorkspace(project_id=project.id, workspace_id=workspace.id))
    db.session.add(ProjectMember(project_id=project.id, user_id=user_id))
    record_activity(user_id, "Created project", name)
    db.session.commit()
    return ok({"project": project_payload(project, workspace.id)}, 201)

@app.delete("/api/projects/<int:project_id>")
@jwt_required()
def delete_project_extra(project_id):
    user_id = int(get_jwt_identity()); membership, workspace = selected_workspace(user_id)
    if not membership or membership.role not in {"Admin", "Manager"}:
        return error("You do not have permission to delete projects.", 403, "FORBIDDEN")
    project = Project.query.join(ProjectWorkspace, ProjectWorkspace.project_id == Project.id).filter(Project.id == project_id, ProjectWorkspace.workspace_id == workspace.id).first()
    if not project: return error("Project not found.", 404, "PROJECT_NOT_FOUND")
    record_activity(user_id, "Deleted project", project.name)
    db.session.delete(project); db.session.commit()
    return ok({"message": "Project deleted."})

@app.post("/api/tasks")
@jwt_required()
def create_task_extra():
    user_id = int(get_jwt_identity()); membership, workspace = selected_workspace(user_id)
    if not membership or membership.role not in {"Admin", "Manager"}:
        return error("You do not have permission to create tasks.", 403, "FORBIDDEN")
    data = request.get_json(silent=True) or {}
    title = clean_string(data.get("title") or data.get("name"), 180)
    description = clean_string(data.get("description"), 4000)
    project_id = data.get("projectId") or data.get("project_id")
    assignee_id = data.get("assigneeId") or data.get("assignee_id")
    status = clean_string(data.get("status") or "Todo", 40)
    priority = clean_string(data.get("priority") or "Medium", 30)
    due_raw = clean_string(data.get("dueDate") or data.get("due_date"), 40) or None
    if not title or not project_id: return error("Task name and project are required.", 400, "VALIDATION_ERROR")
    try: project_id = int(project_id)
    except (TypeError, ValueError): return error("Invalid project.", 400, "VALIDATION_ERROR")
    if status not in TASK_STATUSES: return error("Invalid task status.", 400, "VALIDATION_ERROR")
    if priority not in TASK_PRIORITIES: return error("Invalid task priority.", 400, "VALIDATION_ERROR")
    project = Project.query.join(ProjectWorkspace, ProjectWorkspace.project_id == Project.id).filter(Project.id == project_id, ProjectWorkspace.workspace_id == workspace.id).first()
    if not project: return error("Project not found in this workspace.", 404, "PROJECT_NOT_FOUND")
    if assignee_id:
        try: assignee_id = int(assignee_id)
        except (TypeError, ValueError): return error("Invalid assignee.", 400, "VALIDATION_ERROR")
        if not workspace_user(assignee_id, workspace.id): return error("Assignee must be a member of this workspace.", 400, "INVALID_ASSIGNEE")
    due_date = None
    if due_raw:
        try: due_date = datetime.fromisoformat(due_raw.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError: return error("Invalid due date.", 400, "VALIDATION_ERROR")
    task = Task(title=title, description=description, project_id=project.id, assignee_id=assignee_id, status=status, priority=priority)
    db.session.add(task); db.session.flush(); db.session.add(TaskMeta(task_id=task.id, due_date=due_date))
    record_activity(user_id, "Created task", title)
    if assignee_id and assignee_id != user_id: notify(assignee_id, "Task assigned", f"You were assigned {title}.", "task")
    db.session.commit()
    return ok({"task": task_payload(task)}, 201)

@app.patch("/api/tasks/<int:task_id>")
@jwt_required()
def update_task_extra(task_id):
    user_id = int(get_jwt_identity()); membership, workspace = selected_workspace(user_id)
    task = Task.query.join(ProjectWorkspace, ProjectWorkspace.project_id == Task.project_id).filter(Task.id == task_id, ProjectWorkspace.workspace_id == workspace.id).first() if workspace else None
    if not task: return error("Task not found in this workspace.", 404, "TASK_NOT_FOUND")
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status is not None:
        new_status = clean_string(new_status, 40)
        if new_status not in TASK_STATUSES: return error("Invalid task status.", 400, "VALIDATION_ERROR")
        if membership.role not in {"Admin", "Manager"} and task.assignee_id != user_id:
            return error("You can only update tasks assigned to you.", 403, "FORBIDDEN")
        if new_status != task.status:
            old = task.status; task.status = new_status; record_activity(user_id, "Changed task status", f"{task.title}: {old} → {new_status}")
    for field in ("title", "description", "priority"):
        if field in data:
            value = clean_string(data[field], 4000 if field == "description" else 180)
            if field == "priority" and value not in TASK_PRIORITIES: return error("Invalid task priority.", 400, "VALIDATION_ERROR")
            setattr(task, field, value)
    if "assigneeId" in data and membership.role in {"Admin", "Manager"}:
        aid = data.get("assigneeId")
        task.assignee_id = int(aid) if aid else None
    if "dueDate" in data:
        meta = TaskMeta.query.filter_by(task_id=task.id).first() or TaskMeta(task_id=task.id); db.session.add(meta)
        raw = data.get("dueDate")
        meta.due_date = datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None) if raw else None
    db.session.commit(); return ok({"task": task_payload(task)})

@app.delete("/api/tasks/<int:task_id>")
@jwt_required()
def delete_task_extra(task_id):
    user_id = int(get_jwt_identity()); membership, workspace = selected_workspace(user_id)
    if not membership or membership.role not in {"Admin", "Manager"}: return error("You do not have permission to delete tasks.", 403, "FORBIDDEN")
    task = Task.query.join(ProjectWorkspace, ProjectWorkspace.project_id == Task.project_id).filter(Task.id == task_id, ProjectWorkspace.workspace_id == workspace.id).first()
    if not task: return error("Task not found.", 404, "TASK_NOT_FOUND")
    record_activity(user_id, "Deleted task", task.title); db.session.delete(task); db.session.commit(); return ok({"message": "Task deleted."})

@app.post("/api/team/accept")
@jwt_required()
def accept_invitation_extra():
    token = clean_string((request.get_json(silent=True) or {}).get("token"), 128)
    invitation = WorkspaceInvitation.query.filter_by(token=token).first()
    if not invitation or invitation.accepted_at or invitation.expires_at < now_utc(): return error("This invitation is invalid or expired.", 400, "INVITATION_INVALID")
    user = current_user()
    if user.email.lower() != invitation.email.lower(): return error("This invitation was sent to a different email address.", 403, "INVITATION_EMAIL_MISMATCH")
    membership = Membership.query.filter_by(workspace_id=invitation.workspace_id, user_id=user.id).first()
    if not membership:
        membership = Membership(workspace_id=invitation.workspace_id, user_id=user.id, role=invitation.role); db.session.add(membership)
    invitation.accepted_at = now_utc(); record_activity(user.id, "Joined the workspace", str(invitation.workspace_id)); db.session.commit()
    return ok({"message": "Invitation accepted.", "workspaceId": invitation.workspace_id})

@app.post("/api/team/invite-link")
@jwt_required()
def create_invitation_link_extra():
    user_id = int(get_jwt_identity()); membership, workspace = selected_workspace(user_id)
    if not membership or membership.role not in {"Admin", "Manager"}: return error("You do not have permission to invite members.", 403, "FORBIDDEN")
    data = request.get_json(silent=True) or {}; email = clean_string(data.get("email"), 255).lower(); role = clean_string(data.get("role") or "Member", 40)
    if not EMAIL_RE.match(email) or role not in ALLOWED_ROLES: return error("A valid email and role are required.", 400, "VALIDATION_ERROR")
    invitation = WorkspaceInvitation.query.filter_by(workspace_id=workspace.id, email=email, accepted_at=None).order_by(WorkspaceInvitation.created_at.desc()).first()
    if invitation and invitation.expires_at > now_utc(): invitation.role = role
    else:
        invitation = WorkspaceInvitation(workspace_id=workspace.id, email=email, role=role, token=uuid.uuid4().hex + uuid.uuid4().hex, expires_at=now_utc() + timedelta(days=7)); db.session.add(invitation); db.session.flush()
    existing = User.query.filter(User.email.ilike(email)).first()
    if existing: notify(existing.id, "Workspace invitation", f"You have been invited to {workspace.name} as {role}.", "invite")
    record_activity(user_id, "Invited a workspace member", email); db.session.commit()
    base = os.getenv("FRONTEND_URL", "https://nexora-ops.vercel.app").rstrip("/")
    return ok({"invitation": {"id": invitation.id, "email": invitation.email, "role": invitation.role, "expiresAt": invitation.expires_at.isoformat()}, "invitationLink": f"{base}/invite/{invitation.token}"}, 201)

# Existing app.py contains the read-only dashboard/analytics/activity handlers.
# Replace those handlers with workspace-aware versions so old and invited data stay isolated correctly.
@app.get("/api/dashboard/summary")
@jwt_required()
def dashboard_summary_extra():
    user = current_user(); ensure_workspace_for_user(user); membership, workspace = selected_workspace(user.id); ids = workspace_project_ids(workspace.id) if workspace else []
    tasks = Task.query.filter(Task.project_id.in_(ids)).all() if ids else []; projects = Project.query.filter(Project.id.in_(ids)).order_by(Project.created_at.desc()).all() if ids else []
    counts = {s: sum(t.status == s for t in tasks) for s in TASK_STATUSES}
    return ok({"stats": {"projects": len(projects), "tasks": len(tasks), "completed": counts["Done"], "teamMembers": Membership.query.filter_by(workspace_id=workspace.id).count()}, "taskBreakdown": {"done": counts["Done"], "inProgress": counts["In Progress"], "todo": counts["Todo"], "review": counts["Review"], "blocked": counts["Blocked"]}, "projects": [project_payload(p, workspace.id) for p in projects[:6]], "activity": []})

@app.get("/api/analytics")
@jwt_required()
def analytics_extra():
    user = current_user(); ensure_workspace_for_user(user); membership, workspace = selected_workspace(user.id); ids = workspace_project_ids(workspace.id) if workspace else []
    tasks = Task.query.filter(Task.project_id.in_(ids)).all() if ids else []; projects = Project.query.filter(Project.id.in_(ids)).all() if ids else []
    counts = {s: sum(t.status == s for t in tasks) for s in TASK_STATUSES}; priorities = {p: sum(t.priority == p for t in tasks) for p in TASK_PRIORITIES}; total = len(tasks)
    return ok({"overview": {"completionRate": round(counts["Done"] / total * 100, 1) if total else 0, "totalTasks": total, "completedTasks": counts["Done"], "overdueTasks": 0, "activeProjects": sum(p.status == "Active" for p in projects), "teamMembers": Membership.query.filter_by(workspace_id=workspace.id).count()}, "tasksByStatus": counts, "tasksByPriority": priorities, "projectPerformance": [project_payload(p, workspace.id) for p in projects]})

@app.get("/api/activity")
@jwt_required()
def activity_extra():
    user = current_user(); ensure_workspace_for_user(user); membership, workspace = selected_workspace(user.id)
    rows = Activity.query.join(Membership, Membership.user_id == Activity.user_id).filter(Membership.workspace_id == workspace.id).order_by(Activity.created_at.desc()).limit(100).all()
    return ok({"activity": [{"id": x.id, "action": x.action, "context": x.context or "", "user": {"id": x.user.id, "name": x.user.name, "email": x.user.email, "role": Membership.query.filter_by(user_id=x.user.id, workspace_id=workspace.id).first().role if Membership.query.filter_by(user_id=x.user.id, workspace_id=workspace.id).first() else x.user.role}, "createdAt": x.created_at.isoformat() if x.created_at else None} for x in rows]})

# Flask registers duplicate URL rules in app.py before this module is imported.
# Replace the view functions explicitly so the workspace-aware handlers are the ones executed.
app.view_functions["get_workspace"] = get_selected_workspace_extra
app.view_functions["get_team"] = get_team_extra
app.view_functions["get_projects"] = get_projects_extra
app.view_functions["get_tasks"] = get_tasks_extra
app.view_functions["dashboard_summary"] = dashboard_summary_extra
app.view_functions["analytics"] = analytics_extra
app.view_functions["get_activity"] = activity_extra
app.view_functions["create_project_extra"] = create_project_extra
app.view_functions["create_task_extra"] = create_task_extra
app.view_functions["accept_invitation"] = accept_invitation_extra
app.view_functions["invite_link"] = create_invitation_link_extra
