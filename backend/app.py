import logging
import os
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, func
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

APP_ENV = os.getenv("APP_ENV", "production").lower()
IS_PRODUCTION = APP_ENV == "production"
SECRET_KEY = os.getenv("SECRET_KEY")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///nexora.db")
if IS_PRODUCTION and (not SECRET_KEY or SECRET_KEY == "change-this-in-production"):
    raise RuntimeError("SECRET_KEY must be configured in production.")
if IS_PRODUCTION and (not JWT_SECRET_KEY or JWT_SECRET_KEY == "change-this-jwt-secret-in-production"):
    raise RuntimeError("JWT_SECRET_KEY must be configured in production.")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s")
logger = logging.getLogger("nexora.api")
db = SQLAlchemy()
jwt = JWTManager()
app = Flask(__name__)
app.config.update(SECRET_KEY=SECRET_KEY or "dev-only-secret", JWT_SECRET_KEY=JWT_SECRET_KEY or "dev-only-jwt-secret", JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30"))), JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "30"))), SQLALCHEMY_DATABASE_URI=DATABASE_URL, SQLALCHEMY_TRACK_MODIFICATIONS=False, SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True}, MAX_CONTENT_LENGTH=1024 * 1024)
db.init_app(app)
jwt.init_app(app)
configured_origins=[x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()]
if IS_PRODUCTION and not configured_origins: configured_origins=["https://nexora-ops.vercel.app"]
CORS(app, resources={r"/api/*":{"origins":configured_origins or "*"}}, allow_headers=["Content-Type","Authorization","X-Request-ID"], methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"])
limiter=Limiter(key_func=get_remote_address, app=app, default_limits=["300 per minute"], storage_uri=os.getenv("RATELIMIT_STORAGE_URI","memory://"), headers_enabled=True)
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
class Comment(db.Model):
    __tablename__="task_comments"; id=db.Column(db.Integer,primary_key=True); task_id=db.Column(db.Integer,db.ForeignKey("task.id",ondelete="CASCADE"),nullable=False,index=True); user_id=db.Column(db.Integer,db.ForeignKey("user.id",ondelete="CASCADE"),nullable=False,index=True); body=db.Column(db.Text,nullable=False); created_at=db.Column(db.DateTime,server_default=db.func.now(),index=True)
class Notification(db.Model):
    __tablename__="notifications"; id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey("user.id",ondelete="CASCADE"),nullable=False,index=True); title=db.Column(db.String(180),nullable=False); message=db.Column(db.String(500),nullable=False); kind=db.Column(db.String(40),nullable=False,default="info"); read_at=db.Column(db.DateTime,nullable=True,index=True); created_at=db.Column(db.DateTime,server_default=db.func.now(),index=True)
class RefreshSession(db.Model):
    __tablename__="refresh_sessions"; id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey("user.id",ondelete="CASCADE"),nullable=False,index=True); jti=db.Column(db.String(64),unique=True,nullable=False,index=True); expires_at=db.Column(db.DateTime,nullable=False,index=True); revoked_at=db.Column(db.DateTime,nullable=True,index=True); created_at=db.Column(db.DateTime,server_default=db.func.now())
class WorkspaceInvitation(db.Model):
    __tablename__="workspace_invitations"; id=db.Column(db.Integer,primary_key=True); workspace_id=db.Column(db.Integer,db.ForeignKey("workspaces.id",ondelete="CASCADE"),nullable=False,index=True); email=db.Column(db.String(255),nullable=False,index=True); role=db.Column(db.String(40),nullable=False,default="Member"); token=db.Column(db.String(128),unique=True,nullable=False,index=True); expires_at=db.Column(db.DateTime,nullable=False); accepted_at=db.Column(db.DateTime,nullable=True); created_at=db.Column(db.DateTime,server_default=db.func.now())

def now_utc(): return datetime.now(timezone.utc).replace(tzinfo=None)
def error(message,status=400,code=None,details=None):
    payload={"success":False,"message":message};
    if code: payload["errorCode"]=code
    if details: payload["details"]=details
    payload["requestId"]=getattr(g,"request_id",None); return jsonify(payload),status
def ok(payload=None,status=200):
    body={"success":True};
    if payload: body.update(payload)
    return jsonify(body),status
def clean_string(value,max_len=500): return str(value or "").strip()[:max_len]
def slugify(value):
    slug=re.sub(r"[^a-z0-9]+","-",clean_string(value,120).lower()).strip("-") or "workspace"; base=slug; suffix=2
    while Workspace.query.filter_by(slug=slug).first(): slug=f"{base}-{suffix}"; suffix+=1
    return slug
def user_payload(user): return {"id":user.id,"name":user.name,"email":user.email,"role":user.role}
def workspace_for_user(user_id):
    membership=Membership.query.filter_by(user_id=user_id).order_by(Membership.created_at.asc()).first(); return Workspace.query.get(membership.workspace_id) if membership else None
def membership_for(user_id,workspace_id=None):
    workspace_id=workspace_id or (workspace_for_user(user_id).id if workspace_for_user(user_id) else None); return Membership.query.filter_by(workspace_id=workspace_id,user_id=user_id).first() if workspace_id else None
def require_role(*allowed_roles):
    allowed=set(allowed_roles)
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapped(*args,**kwargs):
            user_id=int(get_jwt_identity()); membership=membership_for(user_id)
            if not membership: return error("You are not a member of a workspace.",403,"WORKSPACE_ACCESS_DENIED")
            if membership.role not in allowed: return error("You do not have permission to perform this action.",403,"FORBIDDEN")
            g.membership=membership; g.workspace=Workspace.query.get(membership.workspace_id); return fn(*args,**kwargs)
        return wrapped
    return decorator
def current_workspace_context(user_id=None):
    user_id=user_id or int(get_jwt_identity()); membership=membership_for(user_id); return membership,Workspace.query.get(membership.workspace_id) if membership else None
def project_in_workspace(project_id,workspace_id): return db.session.query(Project).join(ProjectWorkspace,ProjectWorkspace.project_id==Project.id).filter(Project.id==project_id,ProjectWorkspace.workspace_id==workspace_id).first()
def task_in_workspace(task_id,workspace_id): return db.session.query(Task).join(ProjectWorkspace,ProjectWorkspace.project_id==Task.project_id).filter(Task.id==task_id,ProjectWorkspace.workspace_id==workspace_id).first()
def project_payload(project,workspace_id=None):
    workspace_id=workspace_id or db.session.query(ProjectWorkspace.workspace_id).filter_by(project_id=project.id).scalar(); members=ProjectMember.query.filter_by(project_id=project.id).count()
    return {"id":project.id,"name":project.name,"description":project.description or "","status":project.status,"progress":project.progress,"workspaceId":workspace_id,"memberCount":members,"createdAt":project.created_at.isoformat() if project.created_at else None}
def task_payload(task):
    meta=TaskMeta.query.filter_by(task_id=task.id).first(); assignee=db.session.get(User,task.assignee_id) if task.assignee_id else None; labels=[x for x in (meta.labels.split(",") if meta and meta.labels else []) if x]
    return {"id":task.id,"title":task.title,"description":task.description or "","status":task.status,"priority":task.priority,"projectId":task.project_id,"projectName":task.project.name if task.project else "","assignee":user_payload(assignee) if assignee else None,"dueDate":meta.due_date.isoformat() if meta and meta.due_date else None,"labels":labels,"createdAt":task.created_at.isoformat() if task.created_at else None}
def activity_payload(item): return {"id":item.id,"action":item.action,"context":item.context or "","user":user_payload(item.user) if item.user else None,"createdAt":item.created_at.isoformat() if item.created_at else None}
def notification_payload(item): return {"id":item.id,"title":item.title,"message":item.message,"kind":item.kind,"read":item.read_at is not None,"createdAt":item.created_at.isoformat() if item.created_at else None}
def record_activity(user_id,action,context="",workspace_id=None): db.session.add(Activity(user_id=user_id,action=action,context=context))
def notify(user_id,title,message,kind="info"):
    if user_id: db.session.add(Notification(user_id=user_id,title=title,message=message,kind=kind))
def token_response(user): return {"accessToken":create_access_token(identity=str(user.id)),"refreshToken":create_refresh_token(identity=str(user.id)),"user":user_payload(user)}
def validate_password(password):
    if len(password)<8:return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]",password) or not re.search(r"\d",password):return "Password must contain at least one letter and one number."
    return None

@app.before_request
def start_request():
    g.request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4()); g.request_started=time.perf_counter()
@app.after_request
def finish_request(response):
    response.headers["X-Request-ID"]=getattr(g,"request_id","-"); response.headers["X-Content-Type-Options"]="nosniff"; response.headers["X-Frame-Options"]="DENY"; response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
    if IS_PRODUCTION: response.headers["Strict-Transport-Security"]="max-age=31536000; includeSubDomains"
    return response
@app.errorhandler(Exception)
def handle_unexpected_error(exc): db.session.rollback(); logger.exception("Unhandled application error",extra={"request_id":getattr(g,"request_id","-")}); return error("Internal server error. Please try again.",500,"INTERNAL_ERROR")
@jwt.unauthorized_loader
def jwt_missing(reason): return error("Authorization token is required.",401,"AUTH_REQUIRED")
@jwt.invalid_token_loader
def jwt_invalid(reason): return error("Invalid authorization token.",401,"AUTH_INVALID")
@jwt.expired_token_loader
def jwt_expired(header,payload): return error("Token expired. Please refresh your session.",401,"AUTH_EXPIRED")

@app.get("/")
def root(): return ok({"message":"Nexora API is running","health":"/api/health","api":"/api"})
@app.get("/api/health")
def health():
    try: db.session.execute(db.text("SELECT 1")); return ok({"message":"Nexora API is running","database":"connected","environment":APP_ENV})
    except Exception: db.session.rollback(); return error("Database unavailable.",503,"DATABASE_UNAVAILABLE")

@app.post("/api/auth/register")
@limiter.limit("8 per minute")
def register():
    data=request.get_json(silent=True) or {}; name=clean_string(data.get("name"),100); email=clean_string(data.get("email"),255).lower(); password=str(data.get("password") or ""); workspace_name=clean_string(data.get("workspaceName") or f"{name}'s Workspace",160)
    if len(name)<2 or not EMAIL_RE.match(email): return error("Enter a valid name and email address.",400,"VALIDATION_ERROR")
    password_error=validate_password(password)
    if password_error:return error(password_error,400,"WEAK_PASSWORD")
    if User.query.filter(func.lower(User.email)==email).first():return error("An account with this email already exists.",409,"EMAIL_EXISTS")
    user=User(name=name,email=email,password_hash=generate_password_hash(password,method="scrypt"),role="Admin"); db.session.add(user); db.session.flush(); workspace=Workspace(name=workspace_name,slug=slugify(workspace_name),owner_id=user.id); db.session.add(workspace); db.session.flush(); db.session.add(Membership(workspace_id=workspace.id,user_id=user.id,role="Admin")); record_activity(user.id,"Created the workspace",workspace.name); db.session.commit(); response=token_response(user); response["workspace"]={"id":workspace.id,"name":workspace.name,"slug":workspace.slug,"role":"Admin"}; return ok(response,201)
@app.post("/api/auth/login")
@limiter.limit("10 per minute")
def login():
    data=request.get_json(silent=True) or {}; email=clean_string(data.get("email"),255).lower(); password=str(data.get("password") or ""); user=User.query.filter(func.lower(User.email)==email).first()
    if not user or not check_password_hash(user.password_hash,password):return error("Invalid email or password.",401,"INVALID_CREDENTIALS")
    ensure_user_workspace(user); db.session.commit(); response=token_response(user); workspace=workspace_for_user(user.id); response["workspace"]={"id":workspace.id,"name":workspace.name,"slug":workspace.slug,"role":membership_for(user.id).role}; return ok(response)
@app.post("/api/auth/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id=int(get_jwt_identity()); user=db.session.get(User,user_id); return error("User not found.",401,"AUTH_INVALID") if not user else ok({"accessToken":create_access_token(identity=str(user.id))})
@app.post("/api/auth/logout")
@jwt_required()
def logout(): record_activity(int(get_jwt_identity()),"Signed out","Authentication"); db.session.commit(); return ok({"message":"Logged out successfully."})
@app.get("/api/auth/me")
@jwt_required()
def me():
    user=db.session.get(User,int(get_jwt_identity()));
    if not user:return error("User not found.",404,"USER_NOT_FOUND")
    ensure_user_workspace(user); membership,workspace=current_workspace_context(user.id); db.session.commit(); return ok({"user":user_payload(user),"workspace":{"id":workspace.id,"name":workspace.name,"slug":workspace.slug,"role":membership.role} if workspace else None})

def ensure_user_workspace(user):
    membership=Membership.query.filter_by(user_id=user.id).first()
    if membership:return Workspace.query.get(membership.workspace_id)
    workspace=Workspace(name=f"{user.name}'s Workspace",slug=slugify(f"{user.name}-workspace"),owner_id=user.id); db.session.add(workspace); db.session.flush(); db.session.add(Membership(workspace_id=workspace.id,user_id=user.id,role="Admin")); return workspace
@app.get("/api/workspace")
@jwt_required()
def get_workspace():
    user_id=int(get_jwt_identity()); workspace=ensure_user_workspace(db.session.get(User,user_id)); db.session.commit(); membership=membership_for(user_id,workspace.id); return ok({"workspace":{"id":workspace.id,"name":workspace.name,"slug":workspace.slug,"role":membership.role}})
@app.patch("/api/workspace")
@require_role("Admin")
def update_workspace():
    name=clean_string((request.get_json(silent=True) or {}).get("name"),160)
    if len(name)<2:return error("Workspace name is required.",400,"VALIDATION_ERROR")
    g.workspace.name=name; record_activity(int(get_jwt_identity()),"Updated workspace settings",name); db.session.commit(); return ok({"workspace":{"id":g.workspace.id,"name":g.workspace.name,"slug":g.workspace.slug,"role":g.membership.role}})
@app.get("/api/team")
@jwt_required()
def get_team():
    user_id=int(get_jwt_identity()); membership,workspace=current_workspace_context(user_id)
    if not membership:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
    members=db.session.query(User,Membership).join(Membership,Membership.user_id==User.id).filter(Membership.workspace_id==workspace.id).order_by(Membership.created_at.asc()).all()
    return ok({"members":[{**user_payload(user),"role":membership.role,"joinedAt":membership.created_at.isoformat() if membership.created_at else None} for user,membership in members]})
@app.post("/api/team/invite")
@require_role("Admin","Manager")
def invite_member():
    data=request.get_json(silent=True) or {}; email=clean_string(data.get("email"),255).lower(); role=clean_string(data.get("role") or "Member",40)
    if not EMAIL_RE.match(email) or role not in ROLES:return error("A valid email and role are required.",400,"VALIDATION_ERROR")
    token=uuid.uuid4().hex+uuid.uuid4().hex; invitation=WorkspaceInvitation(workspace_id=g.workspace.id,email=email,role=role,token=token,expires_at=now_utc()+timedelta(days=7)); db.session.add(invitation); existing=User.query.filter(func.lower(User.email)==email).first()
    if existing:notify(existing.id,"Workspace invitation",f"You have been invited to {g.workspace.name} as {role}.","invite")
    record_activity(int(get_jwt_identity()),"Invited a workspace member",email); db.session.commit(); return ok({"invitation":{"id":invitation.id,"email":email,"role":role,"expiresAt":invitation.expires_at.isoformat()}},201)
@app.post("/api/team/accept")
@jwt_required()
def accept_invitation():
    token=clean_string((request.get_json(silent=True) or {}).get("token"),128); invitation=WorkspaceInvitation.query.filter_by(token=token).first()
    if not invitation or invitation.accepted_at or invitation.expires_at<now_utc():return error("This invitation is invalid or expired.",400,"INVITATION_INVALID")
    user_id=int(get_jwt_identity()); user=db.session.get(User,user_id)
    if user.email.lower()!=invitation.email.lower():return error("This invitation was sent to a different email address.",403,"INVITATION_EMAIL_MISMATCH")
    if not Membership.query.filter_by(workspace_id=invitation.workspace_id,user_id=user_id).first():db.session.add(Membership(workspace_id=invitation.workspace_id,user_id=user_id,role=invitation.role))
    invitation.accepted_at=now_utc(); record_activity(user_id,"Joined the workspace",str(invitation.workspace_id)); db.session.commit(); return ok({"message":"Invitation accepted."})
@app.patch("/api/team/<int:member_id>")
@require_role("Admin")
def update_member_role(member_id):
    membership=Membership.query.filter_by(workspace_id=g.workspace.id,user_id=member_id).first()
    if not membership:return error("Team member not found.",404,"MEMBER_NOT_FOUND")
    role=clean_string((request.get_json(silent=True) or {}).get("role"),40)
    if role not in ROLES:return error("Invalid role.",400,"VALIDATION_ERROR")
    if member_id==g.workspace.owner_id and role!="Admin":return error("The workspace owner must remain an Admin.",400,"OWNER_ROLE_REQUIRED")
    membership.role=role; record_activity(int(get_jwt_identity()),"Changed team member role",f"{member_id} → {role}"); db.session.commit(); return ok({"member":{**user_payload(db.session.get(User,member_id)),"role":role}})
@app.delete("/api/team/<int:member_id>")
@require_role("Admin")
def remove_member(member_id):
    if member_id==g.workspace.owner_id:return error("The workspace owner cannot be removed.",400,"OWNER_PROTECTED")
    membership=Membership.query.filter_by(workspace_id=g.workspace.id,user_id=member_id).first()
    if not membership:return error("Team member not found.",404,"MEMBER_NOT_FOUND")
    db.session.delete(membership); record_activity(int(get_jwt_identity()),"Removed a team member",str(member_id)); db.session.commit(); return ok({"message":"Team member removed."})

@app.get("/api/projects")
@jwt_required()
def get_projects():
    user_id=int(get_jwt_identity()); membership,workspace=current_workspace_context(user_id)
    if not membership:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
    projects=db.session.query(Project).join(ProjectWorkspace,ProjectWorkspace.project_id==Project.id).filter(ProjectWorkspace.workspace_id==workspace.id).order_by(Project.created_at.desc()).all(); return ok({"projects":[project_payload(p,workspace.id) for p in projects]})
@app.post("/api/projects")
@require_role("Admin","Manager","Member")
def create_project():
    data=request.get_json(silent=True) or {}; name=clean_string(data.get("name"),160); status=clean_string(data.get("status") or "Active",40)
    if not name:return error("Project name is required.",400,"VALIDATION_ERROR")
    if status not in PROJECT_STATUSES:return error("Invalid project status.",400,"VALIDATION_ERROR")
    try:progress=max(0,min(100,int(data.get("progress",0) or 0)))
    except (TypeError,ValueError):return error("Progress must be a number from 0 to 100.",400,"VALIDATION_ERROR")
    user_id=int(get_jwt_identity()); project=Project(name=name,description=clean_string(data.get("description"),5000),status=status,progress=progress,owner_id=user_id); db.session.add(project); db.session.flush(); db.session.add(ProjectWorkspace(project_id=project.id,workspace_id=g.workspace.id)); db.session.add(ProjectMember(project_id=project.id,user_id=user_id)); record_activity(user_id,"Created a project",name); db.session.commit(); return ok({"project":project_payload(project,g.workspace.id)},201)
@app.patch("/api/projects/<int:project_id>")
@jwt_required()
def update_project(project_id):
    user_id=int(get_jwt_identity()); membership,workspace=current_workspace_context(user_id)
    if not membership or membership.role=="Viewer":return error("You do not have permission to edit projects.",403,"FORBIDDEN")
    project=project_in_workspace(project_id,workspace.id)
    if not project:return error("Project not found.",404,"PROJECT_NOT_FOUND")
    data=request.get_json(silent=True) or {}
    if "name" in data and clean_string(data["name"],160):project.name=clean_string(data["name"],160)
    if "description" in data:project.description=clean_string(data["description"],5000)
    if "status" in data:
        status=clean_string(data["status"],40)
        if status not in PROJECT_STATUSES:return error("Invalid project status.",400,"VALIDATION_ERROR")
        project.status=status
    record_activity(user_id,"Updated a project",project.name); db.session.commit(); return ok({"project":project_payload(project,workspace.id)})
@app.delete("/api/projects/<int:project_id>")
@require_role("Admin","Manager")
def delete_project(project_id):
    project=project_in_workspace(project_id,g.workspace.id)
    if not project:return error("Project not found.",404,"PROJECT_NOT_FOUND")
    record_activity(int(get_jwt_identity()),"Deleted a project",project.name); db.session.delete(project); db.session.commit(); return ok({"message":"Project deleted."})

@app.get("/api/tasks")
@jwt_required()
def get_tasks():
    user_id=int(get_jwt_identity()); membership,workspace=current_workspace_context(user_id)
    if not membership:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
    tasks=db.session.query(Task).join(ProjectWorkspace,ProjectWorkspace.project_id==Task.project_id).filter(ProjectWorkspace.workspace_id==workspace.id).order_by(Task.created_at.desc()).all(); return ok({"tasks":[task_payload(t) for t in tasks]})
@app.post("/api/tasks")
@jwt_required()
def create_task():
    user_id=int(get_jwt_identity()); membership,workspace=current_workspace_context(user_id)
    if not membership or membership.role=="Viewer":return error("You do not have permission to create tasks.",403,"FORBIDDEN")
    data=request.get_json(silent=True) or {}; title=clean_string(data.get("title"),180)
    if not title or not data.get("projectId"):return error("Task title and project are required.",400,"VALIDATION_ERROR")
    try:project_id=int(data.get("projectId"))
    except (TypeError,ValueError):return error("Invalid project.",400,"VALIDATION_ERROR")
    project=project_in_workspace(project_id,workspace.id)
    if not project:return error("Project not found.",404,"PROJECT_NOT_FOUND")
    status=clean_string(data.get("status") or "Todo",40); priority=clean_string(data.get("priority") or "Medium",30)
    if status not in TASK_STATUSES or priority not in TASK_PRIORITIES:return error("Invalid task status or priority.",400,"VALIDATION_ERROR")
    assignee_id=data.get("assigneeId")
    if assignee_id:
        try:assignee_id=int(assignee_id)
        except (TypeError,ValueError):return error("Invalid assignee.",400,"VALIDATION_ERROR")
        if not Membership.query.filter_by(workspace_id=workspace.id,user_id=assignee_id).first():return error("Assignee is not a workspace member.",400,"INVALID_ASSIGNEE")
    task=Task(title=title,description=clean_string(data.get("description"),10000),status=status,priority=priority,project_id=project.id,assignee_id=assignee_id); db.session.add(task); db.session.flush(); due_date=None
    if data.get("dueDate"):
        try:due_date=datetime.fromisoformat(str(data["dueDate"]).replace("Z","+00:00")).replace(tzinfo=None)
        except ValueError:return error("Invalid due date.",400,"VALIDATION_ERROR")
    labels=data.get("labels") or []; labels=labels if isinstance(labels,list) else [str(labels)]; db.session.add(TaskMeta(task_id=task.id,due_date=due_date,labels=",".join(clean_string(x,40) for x in labels[:10]))); record_activity(user_id,"Created a task",task.title)
    if assignee_id and assignee_id!=user_id:notify(assignee_id,"New task assigned",f"You were assigned '{task.title}' in {project.name}.","task")
    db.session.commit(); refresh_project_progress(task.project_id); db.session.commit(); return ok({"task":task_payload(task)},201)
@app.patch("/api/tasks/<int:task_id>")
@jwt_required()
def update_task(task_id):
    user_id=int(get_jwt_identity()); membership,workspace=current_workspace_context(user_id); task=task_in_workspace(task_id,workspace.id) if workspace else None
    if not task:return error("Task not found.",404,"TASK_NOT_FOUND")
    if membership.role=="Viewer":return error("You do not have permission to update tasks.",403,"FORBIDDEN")
    data=request.get_json(silent=True) or {}
    if "status" in data:
        status=clean_string(data["status"],40)
        if status not in TASK_STATUSES:return error("Invalid task status.",400,"VALIDATION_ERROR")
        task.status=status
    if "priority" in data:
        priority=clean_string(data["priority"],30)
        if priority not in TASK_PRIORITIES:return error("Invalid task priority.",400,"VALIDATION_ERROR")
        task.priority=priority
    if "title" in data and clean_string(data["title"],180):task.title=clean_string(data["title"],180)
    if "description" in data:task.description=clean_string(data["description"],10000)
    if "assigneeId" in data:
        assignee_id=data["assigneeId"]
        if assignee_id is not None:
            try:assignee_id=int(assignee_id)
            except (TypeError,ValueError):return error("Invalid assignee.",400,"VALIDATION_ERROR")
            if not Membership.query.filter_by(workspace_id=workspace.id,user_id=assignee_id).first():return error("Assignee is not a workspace member.",400,"INVALID_ASSIGNEE")
        task.assignee_id=assignee_id
    meta=TaskMeta.query.filter_by(task_id=task.id).first() or TaskMeta(task_id=task.id); db.session.add(meta) if not meta.id else None
    if "dueDate" in data:
        if data["dueDate"]:
            try:meta.due_date=datetime.fromisoformat(str(data["dueDate"]).replace("Z","+00:00")).replace(tzinfo=None)
            except ValueError:return error("Invalid due date.",400,"VALIDATION_ERROR")
        else:meta.due_date=None
    record_activity(user_id,"Updated a task",task.title)
    if task.assignee_id and task.assignee_id!=user_id:notify(task.assignee_id,"Task updated",f"'{task.title}' was updated.","task")
    db.session.commit(); refresh_project_progress(task.project_id); db.session.commit(); return ok({"task":task_payload(task)})
@app.delete("/api/tasks/<int:task_id>")
@jwt_required()
def delete_task(task_id):
    user_id=int(get_jwt_identity()); membership,workspace=current_workspace_context(user_id); task=task_in_workspace(task_id,workspace.id) if workspace else None
    if not task:return error("Task not found.",404,"TASK_NOT_FOUND")
    if membership.role not in {"Admin","Manager"} and task.assignee_id!=user_id:return error("You do not have permission to delete this task.",403,"FORBIDDEN")
    project_id=task.project_id; record_activity(user_id,"Deleted a task",task.title); db.session.delete(task); db.session.commit(); refresh_project_progress(project_id); db.session.commit(); return ok({"message":"Task deleted."})
def refresh_project_progress(project_id):
    project=db.session.get(Project,project_id)
    if not project:return
    total=Task.query.filter_by(project_id=project_id).count(); done=Task.query.filter_by(project_id=project_id,status="Done").count(); project.progress=round((done/total)*100) if total else 0

@app.get("/api/dashboard/summary")
@jwt_required()
def dashboard_summary():
    user_id=int(get_jwt_identity()); membership,workspace=current_workspace_context(user_id)
    if not membership:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
    project_ids=[x[0] for x in db.session.query(ProjectWorkspace.project_id).filter_by(workspace_id=workspace.id).all()]; tasks=Task.query.filter(Task.project_id.in_(project_ids)).all() if project_ids else []; completed=sum(t.status=="Done" for t in tasks); projects=Project.query.filter(Project.id.in_(project_ids)).order_by(Project.created_at.desc()).all() if project_ids else []; activities=Activity.query.join(Membership,Membership.user_id==Activity.user_id).filter(Membership.workspace_id==workspace.id).order_by(Activity.created_at.desc()).limit(8).all(); member_count=Membership.query.filter_by(workspace_id=workspace.id).count()
    return ok({"stats":{"projects":len(projects),"tasks":len(tasks),"completed":completed,"teamMembers":member_count},"taskBreakdown":{"done":completed,"inProgress":sum(t.status=="In Progress" for t in tasks),"todo":sum(t.status=="Todo" for t in tasks),"review":sum(t.status=="Review" for t in tasks),"blocked":sum(t.status=="Blocked" for t in tasks)},"projects":[project_payload(p,workspace.id) for p in projects[:6]],"activity":[activity_payload(a) for a in activities]})
@app.get("/api/analytics")
@jwt_required()
def analytics():
    user_id=int(get_jwt_identity()); membership,workspace=current_workspace_context(user_id)
    if not membership:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
    project_ids=[x[0] for x in db.session.query(ProjectWorkspace.project_id).filter_by(workspace_id=workspace.id).all()]; tasks=Task.query.filter(Task.project_id.in_(project_ids)).all() if project_ids else []; total=len(tasks); completed=sum(t.status=="Done" for t in tasks); projects=Project.query.filter(Project.id.in_(project_ids)).all() if project_ids else []
    return ok({"overview":{"completionRate":round((completed/total)*100,1) if total else 0,"totalTasks":total,"completedTasks":completed,"activeProjects":sum(p.status=="Active" for p in projects),"teamMembers":Membership.query.filter_by(workspace_id=workspace.id).count()},"tasksByStatus":{status:sum(t.status==status for t in tasks) for status in TASK_STATUSES},"tasksByPriority":{priority:sum(t.priority==priority for t in tasks) for priority in TASK_PRIORITIES},"projectPerformance":[project_payload(p,workspace.id) for p in projects]})
@app.get("/api/activity")
@jwt_required()
def get_activity():
    user_id=int(get_jwt_identity()); membership,workspace=current_workspace_context(user_id)
    if not membership:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
    activities=Activity.query.join(Membership,Membership.user_id==Activity.user_id).filter(Membership.workspace_id==workspace.id).order_by(Activity.created_at.desc()).limit(100).all(); return ok({"activity":[activity_payload(a) for a in activities]})
@app.delete("/api/activity/<int:activity_id>")
@jwt_required()
def delete_activity(activity_id):
    user_id=int(get_jwt_identity()); membership,workspace=current_workspace_context(user_id)
    if not membership or membership.role!="Admin":return error("Only Admins can delete activity.",403,"FORBIDDEN")
    activity=db.session.query(Activity).join(Membership,Membership.user_id==Activity.user_id).filter(Activity.id==activity_id,Membership.workspace_id==workspace.id).first()
    if not activity:return error("Activity not found.",404,"ACTIVITY_NOT_FOUND")
    db.session.delete(activity); db.session.commit(); return ok({"message":"Activity deleted successfully."})
@app.get("/api/notifications")
@jwt_required()
def get_notifications():
    user_id=int(get_jwt_identity()); items=Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(50).all(); unread=Notification.query.filter_by(user_id=user_id,read_at=None).count(); return ok({"notifications":[notification_payload(n) for n in items],"unread":unread})
@app.patch("/api/notifications/<int:notification_id>/read")
@jwt_required()
def read_notification(notification_id):
    item=Notification.query.filter_by(id=notification_id,user_id=int(get_jwt_identity())).first()
    if not item:return error("Notification not found.",404,"NOTIFICATION_NOT_FOUND")
    item.read_at=now_utc(); db.session.commit(); return ok({"notification":notification_payload(item)})
@app.post("/api/notifications/read-all")
@jwt_required()
def read_all_notifications():
    Notification.query.filter_by(user_id=int(get_jwt_identity()),read_at=None).update({"read_at":now_utc()},synchronize_session=False); db.session.commit(); return ok({"message":"Notifications marked as read."})

def bootstrap_legacy_data():
    users=User.query.all(); changed=False
    for user in users:
        workspace=ensure_user_workspace(user); project_links={x.project_id for x in ProjectWorkspace.query.filter_by(workspace_id=workspace.id).all()}
        for project in Project.query.filter_by(owner_id=user.id).all():
            if project.id not in project_links:
                db.session.add(ProjectWorkspace(project_id=project.id,workspace_id=workspace.id));
                if not ProjectMember.query.filter_by(project_id=project.id,user_id=user.id).first():db.session.add(ProjectMember(project_id=project.id,user_id=user.id))
                changed=True
        changed=True
    if changed:db.session.commit()
with app.app_context():
    db.create_all(); bootstrap_legacy_data()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")),debug=False)
