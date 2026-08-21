import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, get_jwt_identity, jwt_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, func
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
APP_ENV=os.getenv("APP_ENV","production").lower()
IS_PRODUCTION=APP_ENV=="production"
SECRET_KEY=os.getenv("SECRET_KEY")
JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY")
DATABASE_URL=os.getenv("DATABASE_URL","sqlite:///nexora.db")
if DATABASE_URL.startswith("postgres://"): DATABASE_URL=DATABASE_URL.replace("postgres://","postgresql+psycopg://",1)
elif DATABASE_URL.startswith("postgresql://"): DATABASE_URL=DATABASE_URL.replace("postgresql://","postgresql+psycopg://",1)
if IS_PRODUCTION and not SECRET_KEY: raise RuntimeError("SECRET_KEY must be configured in production.")
if IS_PRODUCTION and not JWT_SECRET_KEY: raise RuntimeError("JWT_SECRET_KEY must be configured in production.")

logging.basicConfig(level=getattr(logging,os.getenv("LOG_LEVEL","INFO").upper(),logging.INFO))
logger=logging.getLogger("nexora.api")
db=SQLAlchemy()
jwt=JWTManager()
app=Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY or "dev-secret",
    JWT_SECRET_KEY=JWT_SECRET_KEY or "dev-jwt-secret",
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES","30"))),
    JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=int(os.getenv("JWT_REFRESH_DAYS","30"))),
    SQLALCHEMY_DATABASE_URI=DATABASE_URL,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping":True},
    MAX_CONTENT_LENGTH=1024*1024,
)
db.init_app(app); jwt.init_app(app)
origins=re.compile(r"^https://([a-z0-9-]+\.)?vercel\.app$|^https://nexora-ops\.vercel\.app$",re.I) if IS_PRODUCTION else "*"
CORS(app,resources={r"/api/*":{"origins":origins}},allow_headers=["Content-Type","Authorization","X-Workspace-ID","X-Request-ID"],methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"])
limiter=Limiter(key_func=get_remote_address,app=app,default_limits=["300 per minute"],storage_uri=os.getenv("RATELIMIT_STORAGE_URI","memory://"))

EMAIL_RE=re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ROLES={"Admin","Manager","Member","Viewer"}
PROJECT_STATUSES={"Active","On Hold","Completed","Archived"}
TASK_STATUSES={"Todo","In Progress","Review","Done","Blocked"}
TASK_PRIORITIES={"Low","Medium","High","Critical"}

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(100),nullable=False); email=db.Column(db.String(255),unique=True,nullable=False,index=True); password_hash=db.Column(db.String(255),nullable=False); role=db.Column(db.String(40),nullable=False,default="Member"); created_at=db.Column(db.DateTime,server_default=db.func.now(),index=True)
class Project(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(160),nullable=False); description=db.Column(db.Text,default=""); status=db.Column(db.String(40),nullable=False,default="Active"); progress=db.Column(db.Integer,nullable=False,default=0); owner_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True); created_at=db.Column(db.DateTime,server_default=db.func.now(),index=True); owner=db.relationship("User",foreign_keys=[owner_id]); tasks=db.relationship("Task",backref="project",lazy=True,cascade="all, delete-orphan")
class Task(db.Model):
    id=db.Column(db.Integer,primary_key=True); title=db.Column(db.String(180),nullable=False); description=db.Column(db.Text,default=""); status=db.Column(db.String(40),nullable=False,default="Todo"); priority=db.Column(db.String(30),nullable=False,default="Medium"); project_id=db.Column(db.Integer,db.ForeignKey("project.id"),nullable=False,index=True); assignee_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=True,index=True); created_at=db.Column(db.DateTime,server_default=db.func.now(),index=True); assignee=db.relationship("User",foreign_keys=[assignee_id])
class Activity(db.Model):
    id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True); action=db.Column(db.String(180),nullable=False); context=db.Column(db.String(180),default=""); created_at=db.Column(db.DateTime,server_default=db.func.now(),index=True); user=db.relationship("User",foreign_keys=[user_id])
class Workspace(db.Model):
    __tablename__="workspaces"; id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(160),nullable=False); slug=db.Column(db.String(180),unique=True,nullable=False,index=True); owner_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True); created_at=db.Column(db.DateTime,server_default=db.func.now(),index=True)
class Membership(db.Model):
    __tablename__="workspace_memberships"; id=db.Column(db.Integer,primary_key=True); workspace_id=db.Column(db.Integer,db.ForeignKey("workspaces.id",ondelete="CASCADE"),nullable=False,index=True); user_id=db.Column(db.Integer,db.ForeignKey("user.id",ondelete="CASCADE"),nullable=False,index=True); role=db.Column(db.String(40),nullable=False,default="Member"); created_at=db.Column(db.DateTime,server_default=db.func.now()); __table_args__=(UniqueConstraint("workspace_id","user_id",name="uq_workspace_member"),)
class ProjectWorkspace(db.Model):
    __tablename__="project_workspaces"; id=db.Column(db.Integer,primary_key=True); project_id=db.Column(db.Integer,db.ForeignKey("project.id",ondelete="CASCADE"),nullable=False,unique=True,index=True); workspace_id=db.Column(db.Integer,db.ForeignKey("workspaces.id",ondelete="CASCADE"),nullable=False,index=True)
class ProjectMember(db.Model):
    __tablename__="project_members"; id=db.Column(db.Integer,primary_key=True); project_id=db.Column(db.Integer,db.ForeignKey("project.id",ondelete="CASCADE"),nullable=False,index=True); user_id=db.Column(db.Integer,db.ForeignKey("user.id",ondelete="CASCADE"),nullable=False,index=True); created_at=db.Column(db.DateTime,server_default=db.func.now()); __table_args__=(UniqueConstraint("project_id","user_id",name="uq_project_member"),)
class TaskMeta(db.Model):
    __tablename__="task_metadata"; id=db.Column(db.Integer,primary_key=True); task_id=db.Column(db.Integer,db.ForeignKey("task.id",ondelete="CASCADE"),nullable=False,unique=True,index=True); due_date=db.Column(db.DateTime,nullable=True,index=True); labels=db.Column(db.Text,default=""); updated_at=db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class Notification(db.Model):
    __tablename__="notifications"; id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey("user.id",ondelete="CASCADE"),nullable=False,index=True); title=db.Column(db.String(180),nullable=False); message=db.Column(db.String(500),nullable=False); kind=db.Column(db.String(40),nullable=False,default="info"); read_at=db.Column(db.DateTime,nullable=True,index=True); created_at=db.Column(db.DateTime,server_default=db.func.now(),index=True)
class WorkspaceInvitation(db.Model):
    __tablename__="workspace_invitations"; id=db.Column(db.Integer,primary_key=True); workspace_id=db.Column(db.Integer,db.ForeignKey("workspaces.id",ondelete="CASCADE"),nullable=False,index=True); email=db.Column(db.String(255),nullable=False,index=True); role=db.Column(db.String(40),nullable=False,default="Member"); token=db.Column(db.String(128),unique=True,nullable=False,index=True); expires_at=db.Column(db.DateTime,nullable=False); accepted_at=db.Column(db.DateTime,nullable=True); created_at=db.Column(db.DateTime,server_default=db.func.now())


def now_utc(): return datetime.now(timezone.utc).replace(tzinfo=None)
def clean(v,n=500): return str(v or "").strip()[:n]
def ok(payload=None,status=200):
    body={"success":True}; body.update(payload or {}); return jsonify(body),status
def error(message,status=400,code=None):
    body={"success":False,"message":message,"requestId":getattr(g,"request_id",None)}
    if code: body["errorCode"]=code
    return jsonify(body),status
def slugify(value):
    base=re.sub(r"[^a-z0-9]+","-",clean(value,120).lower()).strip("-") or "workspace"; slug=base; i=2
    while Workspace.query.filter_by(slug=slug).first(): slug=f"{base}-{i}"; i+=1
    return slug
def user_payload(u): return {"id":u.id,"name":u.name,"email":u.email,"role":u.role}
def ensure_user_workspace(user):
    m=Membership.query.filter_by(user_id=user.id).order_by(Membership.created_at.asc()).first()
    if m: return db.session.get(Workspace,m.workspace_id)
    w=Workspace(name=f"{user.name}'s Workspace",slug=slugify(f"{user.name}-workspace"),owner_id=user.id); db.session.add(w); db.session.flush(); db.session.add(Membership(workspace_id=w.id,user_id=user.id,role="Admin")); return w
def all_user_workspaces(user_id):
    return db.session.query(Workspace,Membership).join(Membership,Membership.workspace_id==Workspace.id).filter(Membership.user_id==user_id).order_by(Membership.created_at.asc()).all()
def current_context(user_id):
    user=db.session.get(User,user_id); ensure_user_workspace(user)
    body=request.get_json(silent=True) if request.is_json else {}
    raw=request.headers.get("X-Workspace-ID") or request.args.get("workspaceId") or (body or {}).get("workspaceId")
    workspace_id=None
    try: workspace_id=int(raw) if raw else None
    except (TypeError,ValueError): workspace_id=None
    if workspace_id:
        m=Membership.query.filter_by(user_id=user_id,workspace_id=workspace_id).first()
        if m: return m,db.session.get(Workspace,workspace_id)
    m=Membership.query.filter_by(user_id=user_id).order_by(Membership.created_at.asc()).first()
    return (m,db.session.get(Workspace,m.workspace_id)) if m else (None,None)
def require_role(*roles):
    def deco(fn):
        @wraps(fn)
        @jwt_required()
        def wrapped(*args,**kwargs):
            m,w=current_context(int(get_jwt_identity()))
            if not m:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
            if m.role not in roles:return error("You do not have permission to perform this action.",403,"FORBIDDEN")
            g.membership=m;g.workspace=w;return fn(*args,**kwargs)
        return wrapped
    return deco
def migrate_legacy_links():
    """Attach old projects to the owner's workspace so existing data is never lost."""
    changed=False
    for p in Project.query.all():
        link=ProjectWorkspace.query.filter_by(project_id=p.id).first()
        if link: continue
        m=Membership.query.filter_by(user_id=p.owner_id).order_by(Membership.created_at.asc()).first()
        if m: db.session.add(ProjectWorkspace(project_id=p.id,workspace_id=m.workspace_id)); changed=True
    for p in Project.query.all():
        link=ProjectWorkspace.query.filter_by(project_id=p.id).first()
        if not link: continue
        for t in Task.query.filter_by(project_id=p.id).all():
            if t.assignee_id and not ProjectMember.query.filter_by(project_id=p.id,user_id=t.assignee_id).first():
                db.session.add(ProjectMember(project_id=p.id,user_id=t.assignee_id)); changed=True
        if not ProjectMember.query.filter_by(project_id=p.id,user_id=p.owner_id).first():
            db.session.add(ProjectMember(project_id=p.id,user_id=p.owner_id)); changed=True
    if changed: db.session.commit()
def project_payload(p):
    link=ProjectWorkspace.query.filter_by(project_id=p.id).first(); return {"id":p.id,"name":p.name,"description":p.description or "","status":p.status,"progress":p.progress,"workspaceId":link.workspace_id if link else None,"memberCount":ProjectMember.query.filter_by(project_id=p.id).count(),"createdAt":p.created_at.isoformat() if p.created_at else None}
def task_payload(t):
    meta=TaskMeta.query.filter_by(task_id=t.id).first(); assignee=db.session.get(User,t.assignee_id) if t.assignee_id else None
    return {"id":t.id,"title":t.title,"description":t.description or "","status":t.status,"priority":t.priority,"projectId":t.project_id,"projectName":t.project.name if t.project else "","assignee":user_payload(assignee) if assignee else None,"dueDate":meta.due_date.isoformat() if meta and meta.due_date else None,"labels":[x for x in (meta.labels.split(",") if meta and meta.labels else []) if x],"createdAt":t.created_at.isoformat() if t.created_at else None}
def refresh_progress(pid):
    p=db.session.get(Project,pid)
    if p:
        total=Task.query.filter_by(project_id=pid).count(); done=Task.query.filter_by(project_id=pid,status="Done").count(); p.progress=round(done*100/total) if total else 0

def token_response(user): return {"accessToken":create_access_token(identity=str(user.id)),"refreshToken":create_refresh_token(identity=str(user.id)),"user":user_payload(user)}

@app.before_request
def before(): g.request_id=request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
@app.after_request
def after(r): r.headers["X-Request-ID"]=g.request_id; return r
@app.get("/")
def root(): return ok({"service":"Nexora API","status":"online","health":"/api/health"})
@app.get("/api/health")
def health():
    try: db.session.execute(db.text("SELECT 1")); return ok({"message":"Nexora API is running","database":"connected","environment":APP_ENV})
    except Exception: db.session.rollback(); logger.exception("health failed"); return error("Database unavailable.",503,"DATABASE_UNAVAILABLE")

@app.post("/api/auth/register")
def register():
    d=request.get_json(silent=True) or {}; name=clean(d.get("name"),100); email=clean(d.get("email"),255).lower(); password=str(d.get("password") or "")
    if len(name)<2 or not EMAIL_RE.match(email): return error("Enter a valid name and email address.",400,"VALIDATION_ERROR")
    if len(password)<8:return error("Password must be at least 8 characters.",400,"WEAK_PASSWORD")
    if User.query.filter(func.lower(User.email)==email).first():return error("An account with this email already exists.",409,"EMAIL_EXISTS")
    u=User(name=name,email=email,password_hash=generate_password_hash(password,method="scrypt"),role="Admin");db.session.add(u);db.session.flush();w=Workspace(name=clean(d.get("workspaceName") or f"{name}'s Workspace",160),slug=slugify(d.get("workspaceName") or f"{name}-workspace"),owner_id=u.id);db.session.add(w);db.session.flush();db.session.add(Membership(workspace_id=w.id,user_id=u.id,role="Admin"));db.session.commit();r=token_response(u);r["workspace"]={"id":w.id,"name":w.name,"slug":w.slug,"role":"Admin"};return ok(r,201)
@app.post("/api/auth/login")
def login():
    d=request.get_json(silent=True) or {};email=clean(d.get("email"),255).lower();password=str(d.get("password") or "")
    try:
        u=User.query.filter(func.lower(User.email)==email).first()
        if not u or not check_password_hash(u.password_hash,password):return error("Invalid email or password.",401,"INVALID_CREDENTIALS")
        w=ensure_user_workspace(u);m=Membership.query.filter_by(user_id=u.id,workspace_id=w.id).first();m.role="Admin" if w.owner_id==u.id else m.role
        migrate_legacy_links();db.session.commit();r=token_response(u);r["workspace"]={"id":w.id,"name":w.name,"slug":w.slug,"role":m.role};return ok(r)
    except Exception:db.session.rollback();logger.exception("login failed");return error("Login failed on the server.",500,"LOGIN_FAILED")
@app.get("/api/auth/me")
@jwt_required()
def me():
    u=db.session.get(User,int(get_jwt_identity()))
    if not u:return error("User not found.",404,"USER_NOT_FOUND")
    m,w=current_context(u.id);migrate_legacy_links();db.session.commit();return ok({"user":user_payload(u),"workspace":{"id":w.id,"name":w.name,"slug":w.slug,"role":m.role} if w else None})
@app.post("/api/auth/refresh")
@jwt_required(refresh=True)
def refresh(): return ok({"accessToken":create_access_token(identity=get_jwt_identity())})

@app.get("/api/workspaces")
@jwt_required()
def workspaces():
    uid=int(get_jwt_identity()); ensure_user_workspace(db.session.get(User,uid)); migrate_legacy_links()
    rows=all_user_workspaces(uid); current_id=int(request.headers.get("X-Workspace-ID") or rows[0][0].id) if rows else None
    return ok({"workspaces":[{"id":w.id,"name":w.name,"slug":w.slug,"role":m.role,"ownerId":w.owner_id,"current":w.id==current_id} for w,m in rows]})
@app.get("/api/workspace")
@jwt_required()
def workspace():
    m,w=current_context(int(get_jwt_identity()));
    if not m:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
    return ok({"workspace":{"id":w.id,"name":w.name,"slug":w.slug,"role":m.role}})

@app.get("/api/team")
@jwt_required()
def team():
    m,w=current_context(int(get_jwt_identity()))
    if not m:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
    rows=db.session.query(User,Membership).join(Membership,Membership.user_id==User.id).filter(Membership.workspace_id==w.id).order_by(Membership.created_at.asc()).all()
    return ok({"members":[{**user_payload(u),"role":mem.role,"joinedAt":mem.created_at.isoformat() if mem.created_at else None} for u,mem in rows]})
@app.post("/api/team/invite")
@require_role("Admin","Manager")
def invite():
    d=request.get_json(silent=True) or {};email=clean(d.get("email"),255).lower();role=clean(d.get("role") or "Member",40)
    if not EMAIL_RE.match(email) or role not in ROLES:return error("A valid email and role are required.",400,"VALIDATION_ERROR")
    inv=WorkspaceInvitation(workspace_id=g.workspace.id,email=email,role=role,token=uuid.uuid4().hex+uuid.uuid4().hex,expires_at=now_utc()+timedelta(days=7));db.session.add(inv);db.session.commit();return ok({"invitation":{"id":inv.id,"email":email,"role":role,"token":inv.token,"expiresAt":inv.expires_at.isoformat()}},201)
@app.post("/api/team/accept")
@jwt_required()
def accept_invite():
    token=clean((request.get_json(silent=True) or {}).get("token"),128);inv=WorkspaceInvitation.query.filter_by(token=token).first();uid=int(get_jwt_identity());u=db.session.get(User,uid)
    if not inv or inv.accepted_at or inv.expires_at<now_utc():return error("This invitation is invalid or expired.",400,"INVITATION_INVALID")
    if u.email.lower()!=inv.email.lower():return error("This invitation was sent to a different email address.",403,"INVITATION_EMAIL_MISMATCH")
    if not Membership.query.filter_by(workspace_id=inv.workspace_id,user_id=uid).first():db.session.add(Membership(workspace_id=inv.workspace_id,user_id=uid,role=inv.role))
    inv.accepted_at=now_utc();db.session.commit();return ok({"message":"Invitation accepted.","workspace":{"id":inv.workspace_id,"role":inv.role}})

@app.get("/api/projects")
@jwt_required()
def projects():
    m,w=current_context(int(get_jwt_identity()));
    if not m:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
    migrate_legacy_links()
    ids=db.session.query(ProjectWorkspace.project_id).filter(ProjectWorkspace.workspace_id==w.id)
    if m.role not in {"Admin","Manager"}:
        assigned_ids=db.session.query(ProjectMember.project_id).filter(ProjectMember.user_id==int(get_jwt_identity()))
        ids=ids.filter(ProjectWorkspace.project_id.in_(assigned_ids))
    ps=Project.query.filter(Project.id.in_(ids)).order_by(Project.created_at.desc()).all()
    return ok({"projects":[project_payload(p) for p in ps]})
@app.post("/api/projects")
@require_role("Admin","Manager")
def create_project():
    d=request.get_json(silent=True) or {};name=clean(d.get("name"),160);desc=clean(d.get("description"),2000)
    if not name:return error("Project name is required.",400,"VALIDATION_ERROR")
    uid=int(get_jwt_identity());p=Project(name=name,description=desc,owner_id=uid);db.session.add(p);db.session.flush();db.session.add(ProjectWorkspace(project_id=p.id,workspace_id=g.workspace.id));db.session.add(ProjectMember(project_id=p.id,user_id=uid));db.session.commit();return ok({"project":project_payload(p)},201)
@app.delete("/api/projects/<int:pid>")
@require_role("Admin","Manager")
def delete_project(pid):
    p=db.session.get(Project,pid)
    if not p or not ProjectWorkspace.query.filter_by(project_id=pid,workspace_id=g.workspace.id).first():return error("Project not found.",404,"PROJECT_NOT_FOUND")
    db.session.delete(p);db.session.commit();return ok({"message":"Project deleted."})

@app.get("/api/tasks")
@jwt_required()
def tasks():
    m,w=current_context(int(get_jwt_identity()));
    if not m:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
    migrate_legacy_links();ids=db.session.query(ProjectWorkspace.project_id).filter(ProjectWorkspace.workspace_id==w.id)
    if m.role not in {"Admin","Manager"}:
        assigned_ids=db.session.query(ProjectMember.project_id).filter(ProjectMember.user_id==int(get_jwt_identity()))
        ids=ids.filter(ProjectWorkspace.project_id.in_(assigned_ids))
    if m.role in {"Admin","Manager"}:
        # Admins and managers see every task in the selected workspace.
        ts=Task.query.filter(Task.project_id.in_(ids)).order_by(Task.created_at.desc()).all()
    else:
        # Members see only tasks assigned to themselves.
        ts=Task.query.filter(Task.project_id.in_(ids),Task.assignee_id==int(get_jwt_identity())).order_by(Task.created_at.desc()).all()
    return ok({"tasks":[task_payload(t) for t in ts]})
@app.post("/api/tasks")
@require_role("Admin","Manager")
def create_task():
    d=request.get_json(silent=True) or {};title=clean(d.get("title"),180);pid=int(d.get("projectId") or 0);assignee=d.get("assigneeId");priority=clean(d.get("priority") or "Medium",30);status=clean(d.get("status") or "Todo",40)
    if not title or not pid:return error("Task title and project are required.",400,"VALIDATION_ERROR")
    if priority not in TASK_PRIORITIES or status not in TASK_STATUSES:return error("Invalid task status or priority.",400,"VALIDATION_ERROR")
    p=Project.query.join(ProjectWorkspace,ProjectWorkspace.project_id==Project.id).filter(Project.id==pid,ProjectWorkspace.workspace_id==g.workspace.id).first()
    if not p:return error("Project not found in this workspace.",404,"PROJECT_NOT_FOUND")
    aid=int(assignee) if assignee else None
    if aid and not Membership.query.filter_by(workspace_id=g.workspace.id,user_id=aid).first():return error("Assignee is not a member of this workspace.",400,"ASSIGNEE_NOT_MEMBER")
    t=Task(title=title,description=clean(d.get("description"),2000),project_id=pid,assignee_id=aid,priority=priority,status=status);db.session.add(t);db.session.flush()
    due=d.get("dueDate");meta=TaskMeta(task_id=t.id)
    if due:
        try: meta.due_date=datetime.fromisoformat(str(due).replace("Z","+00:00")).replace(tzinfo=None)
        except ValueError:return error("Invalid due date.",400,"VALIDATION_ERROR")
    db.session.add(meta)
    if aid and aid!=int(get_jwt_identity()):
        if not ProjectMember.query.filter_by(project_id=pid,user_id=aid).first():db.session.add(ProjectMember(project_id=pid,user_id=aid))
        n=Notification(user_id=aid,title="Task assigned",message=f"You were assigned {title} in {p.name}.",kind="task");db.session.add(n)
    refresh_progress(pid);db.session.commit();return ok({"task":task_payload(t)},201)
@app.patch("/api/tasks/<int:tid>")
@jwt_required()
def update_task(tid):
    uid=int(get_jwt_identity());m,w=current_context(uid);t=Task.query.get(tid)
    if not m or not t or not ProjectWorkspace.query.filter_by(project_id=t.project_id,workspace_id=w.id).first():return error("Task not found.",404,"TASK_NOT_FOUND")
    d=request.get_json(silent=True) or {}
    if m.role not in {"Admin","Manager"} and t.assignee_id!=uid:return error("You can only update tasks assigned to you.",403,"FORBIDDEN")
    if "status" in d and d["status"] in TASK_STATUSES:t.status=d["status"]
    if m.role in {"Admin","Manager"}:
        if "priority" in d and d["priority"] in TASK_PRIORITIES:t.priority=d["priority"]
        if "assigneeId" in d:
            aid=int(d["assigneeId"]) if d["assigneeId"] else None
            if aid and not Membership.query.filter_by(workspace_id=w.id,user_id=aid).first():return error("Assignee is not a workspace member.",400,"ASSIGNEE_NOT_MEMBER")
            t.assignee_id=aid
    refresh_progress(t.project_id);db.session.commit();return ok({"task":task_payload(t)})
@app.delete("/api/tasks/<int:tid>")
@require_role("Admin","Manager")
def delete_task(tid):
    t=Task.query.get(tid);m,w=current_context(int(get_jwt_identity()))
    if not t or not ProjectWorkspace.query.filter_by(project_id=t.project_id,workspace_id=w.id).first():return error("Task not found.",404,"TASK_NOT_FOUND")
    pid=t.project_id;db.session.delete(t);db.session.flush();refresh_progress(pid);db.session.commit();return ok({"message":"Task deleted."})

@app.get("/api/dashboard/summary")
@jwt_required()
def summary():
    m,w=current_context(int(get_jwt_identity()));
    if not m:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
    migrate_legacy_links();ids=db.session.query(ProjectWorkspace.project_id).filter(ProjectWorkspace.workspace_id==w.id)
    if m.role not in {"Admin","Manager"}:
        assigned_ids=db.session.query(ProjectMember.project_id).filter(ProjectMember.user_id==int(get_jwt_identity()))
        ids=ids.filter(ProjectWorkspace.project_id.in_(assigned_ids))
        ts=Task.query.filter(Task.project_id.in_(ids),Task.assignee_id==int(get_jwt_identity())).all()
    else:
        ts=Task.query.filter(Task.project_id.in_(ids)).all()
    ps=Project.query.filter(Project.id.in_(ids)).order_by(Project.created_at.desc()).all();counts={s:sum(t.status==s for t in ts) for s in TASK_STATUSES};members=Membership.query.filter_by(workspace_id=w.id).count();acts=Activity.query.join(Membership,Membership.user_id==Activity.user_id).filter(Membership.workspace_id==w.id).order_by(Activity.created_at.desc()).limit(10).all()
    return ok({"stats":{"projects":len(ps),"tasks":len(ts),"completed":counts["Done"],"teamMembers":members},"taskBreakdown":{"done":counts["Done"],"inProgress":counts["In Progress"],"todo":counts["Todo"],"review":counts["Review"],"blocked":counts["Blocked"]},"projects":[project_payload(p) for p in ps[:6]],"activity":[{"id":a.id,"action":a.action,"context":a.context or ""} for a in acts]})
@app.get("/api/analytics")
@jwt_required()
def analytics():
    m,w=current_context(int(get_jwt_identity()));
    if not m:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
    migrate_legacy_links();ids=db.session.query(ProjectWorkspace.project_id).filter(ProjectWorkspace.workspace_id==w.id);ts=Task.query.filter(Task.project_id.in_(ids)).all();ps=Project.query.filter(Project.id.in_(ids)).all();counts={s:sum(t.status==s for t in ts) for s in TASK_STATUSES};prior={p:sum(t.priority==p for t in ts) for p in TASK_PRIORITIES};total=len(ts)
    return ok({"overview":{"completionRate":round(counts["Done"]*100/total,1) if total else 0,"totalTasks":total,"completedTasks":counts["Done"],"overdueTasks":0,"activeProjects":sum(p.status=="Active" for p in ps),"teamMembers":Membership.query.filter_by(workspace_id=w.id).count()},"tasksByStatus":counts,"tasksByPriority":prior,"projectPerformance":[project_payload(p) for p in ps]})
@app.get("/api/activity")
@jwt_required()
def activity():
    m,w=current_context(int(get_jwt_identity()));
    if not m:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
    rows=Activity.query.join(Membership,Membership.user_id==Activity.user_id).filter(Membership.workspace_id==w.id).order_by(Activity.created_at.desc()).limit(100).all();return ok({"activity":[{"id":a.id,"action":a.action,"context":a.context or "","user":user_payload(a.user) if a.user else None,"createdAt":a.created_at.isoformat() if a.created_at else None} for a in rows]})
@app.delete("/api/activity/<int:aid>")
@require_role("Admin")
def delete_activity(aid):
    m,w=current_context(int(get_jwt_identity()))
    a=Activity.query.get(aid)
    if not m or not a:
        return error("Activity not found.",404,"ACTIVITY_NOT_FOUND")
    if not Membership.query.filter_by(workspace_id=w.id,user_id=a.user_id).first():
        return error("Activity not found.",404,"ACTIVITY_NOT_FOUND")
    db.session.delete(a);db.session.commit();return ok({"message":"Activity deleted."})

@app.get("/api/notifications")
@jwt_required()
def notifications():
    rows=Notification.query.filter_by(user_id=int(get_jwt_identity())).order_by(Notification.created_at.desc()).limit(100).all();return ok({"notifications":[{"id":n.id,"title":n.title,"message":n.message,"kind":n.kind,"read":bool(n.read_at),"createdAt":n.created_at.isoformat() if n.created_at else None} for n in rows]})
@app.patch("/api/notifications/<int:nid>/read")
@jwt_required()
def read_notification(nid):
    n=Notification.query.filter_by(id=nid,user_id=int(get_jwt_identity())).first()
    if not n:return error("Notification not found.",404,"NOTIFICATION_NOT_FOUND")
    n.read_at=now_utc();db.session.commit();return ok({"message":"Notification marked as read."})

@app.errorhandler(404)
def not_found(_):return error("Route not found.",404,"NOT_FOUND")
@app.errorhandler(500)
def internal(_):db.session.rollback();logger.exception("Unhandled request exception");return error("Internal server error.",500,"INTERNAL_ERROR")
with app.app_context():
    db.create_all()
    try: migrate_legacy_links()
    except Exception: db.session.rollback(); logger.exception("legacy migration skipped")
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")),debug=not IS_PRODUCTION)
