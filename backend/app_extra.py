from flask import g, request
from flask_jwt_extended import get_jwt_identity, create_access_token, jwt_required
from app import app, db, User, Workspace, Membership, WorkspaceInvitation, Project, ProjectWorkspace, ProjectMember, Task, TaskMeta, error, ok, require_role, clean_string, EMAIL_RE, now_utc, record_activity, notify, token_response, validate_password, slugify, project_payload, task_payload, TASK_STATUSES, TASK_PRIORITIES
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
import os
import uuid

@app.after_request
def ensure_frontend_cors(response):
    origin=request.headers.get('Origin');allowed={'https://nexora-ops.vercel.app','https://nexora.vercel.app'}
    if origin in allowed:
        response.headers['Access-Control-Allow-Origin']=origin;response.headers['Access-Control-Allow-Headers']='Content-Type, Authorization, X-Request-ID';response.headers['Access-Control-Allow-Methods']='GET, POST, PUT, PATCH, DELETE, OPTIONS';response.headers['Vary']='Origin'
    return response

@app.post('/api/auth/register')
def register_extra():
    data=request.get_json(silent=True) or {};name=clean_string(data.get('name'),100);email=clean_string(data.get('email'),255).lower();password=str(data.get('password') or '')
    if not name or not EMAIL_RE.match(email):return error('Name and a valid email are required.',400,'VALIDATION_ERROR')
    password_error=validate_password(password)
    if password_error:return error(password_error,400,'VALIDATION_ERROR')
    if User.query.filter(User.email.ilike(email)).first():return error('An account with this email already exists.',409,'EMAIL_EXISTS')
    user=User(name=name,email=email,password_hash=generate_password_hash(password),role='Admin');db.session.add(user);db.session.flush();workspace=Workspace(name=f"{name}'s Workspace",slug=slugify(f'{name}-workspace'),owner_id=user.id);db.session.add(workspace);db.session.flush();db.session.add(Membership(workspace_id=workspace.id,user_id=user.id,role='Admin'));db.session.commit();return ok(token_response(user),201)

@app.post('/api/auth/login')
def login_extra():
    data=request.get_json(silent=True) or {};email=clean_string(data.get('email'),255).lower();password=str(data.get('password') or '');user=User.query.filter(User.email.ilike(email)).first()
    if not user or not check_password_hash(user.password_hash,password):return error('Invalid email or password.',401,'INVALID_CREDENTIALS')
    return ok(token_response(user))

@app.post('/api/auth/refresh')
@jwt_required(refresh=True)
def refresh_extra():
    user=db.session.get(User,int(get_jwt_identity()))
    if not user:return error('User account not found.',401,'AUTH_INVALID')
    return ok({'accessToken':create_access_token(identity=str(user.id))})

@app.post('/api/projects')
@require_role('Admin','Manager')
def create_project_extra():
    data=request.get_json(silent=True) or {};name=clean_string(data.get('name'),160);description=clean_string(data.get('description'),2000);status=clean_string(data.get('status') or 'Active',40)
    if not name:return error('Project name is required.',400,'VALIDATION_ERROR')
    if status not in {'Active','On Hold','Completed','Archived'}:return error('Invalid project status.',400,'VALIDATION_ERROR')
    project=Project(name=name,description=description,status=status,owner_id=int(get_jwt_identity()));db.session.add(project);db.session.flush();db.session.add(ProjectWorkspace(project_id=project.id,workspace_id=g.workspace.id));db.session.add(ProjectMember(project_id=project.id,user_id=int(get_jwt_identity())));record_activity(int(get_jwt_identity()),'Created project',name);db.session.commit();return ok({'project':project_payload(project,g.workspace.id)},201)

@app.post('/api/tasks')
@require_role('Admin','Manager')
def create_task_extra():
    data=request.get_json(silent=True) or {}
    title=clean_string(data.get('title') or data.get('name'),180)
    description=clean_string(data.get('description'),4000)
    project_id=data.get('projectId') or data.get('project_id')
    assignee_id=data.get('assigneeId') or data.get('assignee_id')
    status=clean_string(data.get('status') or 'Todo',40)
    priority=clean_string(data.get('priority') or 'Medium',30)
    due_date_raw=clean_string(data.get('dueDate') or data.get('due_date'),40) or None
    if not title or not project_id:return error('Task name and project are required.',400,'VALIDATION_ERROR')
    if status not in TASK_STATUSES:return error('Invalid task status.',400,'VALIDATION_ERROR')
    if priority not in TASK_PRIORITIES:return error('Invalid task priority.',400,'VALIDATION_ERROR')
    try: project_id=int(project_id)
    except (TypeError,ValueError):return error('Invalid project.',400,'VALIDATION_ERROR')
    project=Project.query.join(ProjectWorkspace,ProjectWorkspace.project_id==Project.id).filter(Project.id==project_id,ProjectWorkspace.workspace_id==g.workspace.id).first()
    if not project:return error('Project not found in this workspace.',404,'PROJECT_NOT_FOUND')
    if assignee_id:
        try: assignee_id=int(assignee_id)
        except (TypeError,ValueError):return error('Invalid assignee.',400,'VALIDATION_ERROR')
        if not Membership.query.filter_by(workspace_id=g.workspace.id,user_id=assignee_id).first():return error('Assignee must be a member of this workspace.',400,'INVALID_ASSIGNEE')
    due_date=None
    if due_date_raw:
        try: due_date=datetime.fromisoformat(due_date_raw.replace('Z','+00:00')).replace(tzinfo=None)
        except ValueError:return error('Invalid due date.',400,'VALIDATION_ERROR')
    task=Task(title=title,description=description,project_id=project_id,assignee_id=assignee_id,status=status,priority=priority)
    db.session.add(task);db.session.flush();db.session.add(TaskMeta(task_id=task.id,due_date=due_date));record_activity(int(get_jwt_identity()),'Created task',title)
    if assignee_id and assignee_id!=int(get_jwt_identity()):notify(assignee_id,'Task assigned',f'You were assigned {title}.','task')
    db.session.commit();return ok({'task':task_payload(task)},201)

@app.post('/api/team/invite-link')
@require_role('Admin','Manager')
def create_invitation_link():
    data=request.get_json(silent=True) or {};email=clean_string(data.get('email'),255).lower();role=clean_string(data.get('role') or 'Member',40)
    if not EMAIL_RE.match(email) or role not in {'Admin','Manager','Member','Viewer'}:return error('A valid email and role are required.',400,'VALIDATION_ERROR')
    invitation=WorkspaceInvitation.query.filter_by(workspace_id=g.workspace.id,email=email,accepted_at=None).order_by(WorkspaceInvitation.created_at.desc()).first()
    if invitation and invitation.expires_at>now_utc():invitation.role=role
    else:invitation=WorkspaceInvitation(workspace_id=g.workspace.id,email=email,role=role,token=uuid.uuid4().hex+uuid.uuid4().hex,expires_at=now_utc()+timedelta(days=7));db.session.add(invitation);db.session.flush()
    existing_user=User.query.filter(User.email.ilike(email)).first()
    if existing_user:notify(existing_user.id,'Workspace invitation',f'You have been invited to {g.workspace.name} as {role}.','invite')
    record_activity(int(get_jwt_identity()),'Invited a workspace member',email);db.session.commit();base=os.getenv('FRONTEND_URL','https://nexora-ops.vercel.app').rstrip('/');return ok({'invitation':{'id':invitation.id,'email':invitation.email,'role':invitation.role,'expiresAt':invitation.expires_at.isoformat()},'invitationLink':f'{base}/invite/{invitation.token}'},201)
