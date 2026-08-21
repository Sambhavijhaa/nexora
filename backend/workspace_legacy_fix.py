"""Keep legacy projects/tasks visible in the workspace that owns them."""

import runtime_v2
from app import db, Project, ProjectWorkspace, ProjectMember, Task, TaskMeta


def legacy_migrate(user_id, workspace):
    if not workspace:
        return

    # A workspace owns the projects created by its owner. This is important for
    # older records created before ProjectWorkspace was introduced. It also
    # prevents a member's old personal projects from leaking into a friend's
    # workspace.
    owner_id = workspace.owner_id
    changed = False

    for project in Project.query.filter_by(owner_id=owner_id).all():
        link = ProjectWorkspace.query.filter_by(project_id=project.id).first()
        if not link:
            db.session.add(ProjectWorkspace(project_id=project.id, workspace_id=workspace.id))
            changed = True

        # The workspace owner is always a project member for legacy projects.
        if not ProjectMember.query.filter_by(project_id=project.id, user_id=owner_id).first():
            db.session.add(ProjectMember(project_id=project.id, user_id=owner_id))
            changed = True

        for task in Task.query.filter_by(project_id=project.id).all():
            if not TaskMeta.query.filter_by(task_id=task.id).first():
                db.session.add(TaskMeta(task_id=task.id))
                changed = True

    if changed:
        db.session.flush()


runtime_v2.legacy_migrate = legacy_migrate
