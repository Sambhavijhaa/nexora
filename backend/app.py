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
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, get_jwt, get_jwt_identity, jwt_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, func
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
APP_ENV=os.getenv("APP_ENV","production").lower(); IS_PRODUCTION=APP_ENV=="production"; SECRET_KEY=os.getenv("SECRET_KEY"); JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY"); DATABASE_URL=os.getenv("DATABASE_URL","sqlite:///nexora.db")
if IS_PRODUCTION and (not SECRET_KEY or SECRET_KEY=="change-this-in-production"): raise RuntimeError("SECRET_KEY must be configured in production.")
if IS_PRODUCTION and (not JWT_SECRET_KEY or JWT_SECRET_KEY=="change-this-jwt-secret-in-production"): raise RuntimeError("JWT_SECRET_KEY must be configured in production.")
if DATABASE_URL.startswith("postgres://"): DATABASE_URL=DATABASE_URL.replace("postgres://","postgresql+psycopg://",1)
elif DATABASE_URL.startswith("postgresql://"): DATABASE_URL=DATABASE_URL.replace("postgresql://","postgresql+psycopg://",1)
LOG_LEVEL=os.getenv("LOG_LEVEL","INFO").upper(); logging.basicConfig(level=getattr(logging,LOG_LEVEL,logging.INFO),format="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"); logger=logging.getLogger("nexora.api")
db=SQLAlchemy(); jwt=JWTManager(); app=Flask(__name__)
app.config.update(SECRET_KEY=SECRET_KEY or "dev-only-secret",JWT_SECRET_KEY=JWT_SECRET_KEY or "dev-only-jwt-secret",JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES","30"))),JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=int(os.getenv("JWT_REFRESH_DAYS","30"))),SQLALCHEMY_DATABASE_URI=DATABASE_URL,SQLALCHEMY_TRACK_MODIFICATIONS=False,SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping":True},MAX_CONTENT_LENGTH=1024*1024)
db.init_app(app); jwt.init_app(app)
# Authentication is JWT-header based, not cookie based. Allow the production
# Vercel deployment plus Vercel preview deployments so login is not blocked by
# a stale/alternate Vercel hostname.
configured_origins=[x.strip() for x in os.getenv("CORS_ORIGINS","").split(",") if x.strip()]
if IS_PRODUCTION:
    configured_origins = configured_origins or ["https://nexora-ops.vercel.app"]
    cors_origins = re.compile(r"^https://([a-z0-9-]+\.)?vercel\.app$|^https://nexora-ops\.vercel\.app$", re.I)
else:
    cors_origins = configured_origins or "*"
CORS(app,resources={r"/api/*":{"origins":cors_origins}},allow_headers=["Content-Type","Authorization","X-Workspace-ID","X-Request-ID"],methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"])
limiter=Limiter(key_func=get_remote_address,app=app,default_limits=["300 per minute"],storage_uri=os.getenv("RATELIMIT_STORAGE_URI","memory://"),headers_enabled=True)
EMAIL_RE=re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$"); ROLES={"Admin","Manager","Member","Viewer"}; PROJECT_STATUSES={"Active","On Hold","Completed","Archived"}; TASK_STATUSES={"Todo","In Progress","Review","Done","Blocked"}; TASK_PRIORITIES={"Low","Medium","High","Critical"}

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
 payload={"success":False,"message":message}
 if code: payload["errorCode"]=code
 if details: payload["details"]=details
 payload["requestId"]=getattr(g,"request_id",None); return jsonify(payload),status
def ok(payload=None,status=200):
 body={"success":True}
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
 if not workspace_id:
  workspace=workspace_for_user(user_id); workspace_id=workspace.id if workspace else None
 return Membership.query.filter_by(workspace_id=workspace_id,user_id=user_id).first() if workspace_id else None
def current_workspace_context(user_id=None):
 user_id=user_id or int(get_jwt_identity()); membership=membership_for(user_id); return membership,Workspace.query.get(membership.workspace_id) if membership else None
def require_role(*allowed_roles):
 allowed=set(allowed_roles)
 def decorator(fn):
  @wraps(fn)
  @jwt_required()
  def wrapped(*args,**kwargs):
   membership=membership_for(int(get_jwt_identity()))
   if not membership:return error("You are not a member of a workspace.",403,"WORKSPACE_ACCESS_DENIED")
   if membership.role not in allowed:return error("You do not have permission to perform this action.",403,"FORBIDDEN")
   g.membership=membership; g.workspace=Workspace.query.get(membership.workspace_id); return fn(*args,**kwargs)
  return wrapped
 return decorator
def ensure_user_workspace(user):
 membership=Membership.query.filter_by(user_id=user.id).first()
 if membership:return Workspace.query.get(membership.workspace_id)
 workspace=Workspace(name=f"{user.name}'s Workspace",slug=slugify(f"{user.name}-workspace"),owner_id=user.id); db.session.add(workspace); db.session.flush(); db.session.add(Membership(workspace_id=workspace.id,user_id=user.id,role="Admin")); return workspace
def record_activity(user_id,action,context=""): db.session.add(Activity(user_id=user_id,action=action,context=context)
def notify(user_id,title,message,kind="info"):
 if user_id:db.session.add(Notification(user_id=user_id,title=title,message=message,kind=kind))
def refresh_project_progress(project_id):
 project=db.session.get(Project,project_id)
 if not project:return
 total=Task.query.filter_by(project_id=project_id).count(); done=Task.query.filter_by(project_id=project_id,status="Done").count(); project.progress=round((done/total)*100) if total else 0
def project_in_workspace(project_id,workspace_id):return db.session.query(Project).join(ProjectWorkspace,ProjectWorkspace.project_id==Project.id).filter(Project.id==project_id,ProjectWorkspace.workspace_id==workspace_id).first()
def task_in_workspace(task_id,workspace_id):return db.session.query(Task).join(ProjectWorkspace,ProjectWorkspace.project_id==Task.project_id).filter(Task.id==task_id,ProjectWorkspace.workspace_id==workspace_id).first()
def project_payload(project,workspace_id=None):
 workspace_id=workspace_id or db.session.query(ProjectWorkspace.workspace_id).filter_by(project_id=project.id).scalar(); return {"id":project.id,"name":project.name,"description":project.description or "","status":project.status,"progress":project.progress,"workspaceId":workspace_id,"memberCount":ProjectMember.query.filter_by(project_id=project.id).count(),"createdAt":project.created_at.isoformat() if project.created_at else None}
def task_payload(task):
 meta=TaskMeta.query.filter_by(task_id=task.id).first(); assignee=db.session.get(User,task.assignee_id) if task.assignee_id else None; return {"id":task.id,"title":task.title,"description":task.description or "","status":task.status,"priority":task.priority,"projectId":task.project_id,"projectName":task.project.name if task.project else "","assignee":user_payload(assignee) if assignee else None,"dueDate":meta.due_date.isoformat() if meta and meta.due_date else None,"labels":[x for x in (meta.labels.split(",") if meta and meta.labels else []) if x],"createdAt":task.created_at.isoformat() if task.created_at else None}
def activity_payload(item):return {"id":item.id,"action":item.action,"context":item.context or "","user":user_payload(item.user) if item.user else None,"createdAt":item.created_at.isoformat() if item.created_at else None}
def notification_payload(item):return {"id":item.id,"title":item.title,"message":item.message,"kind":item.kind,"read":bool(item.read_at),"createdAt":item.created_at.isoformat() if item.created_at else None}
def validate_password(password):
 if len(password)<8:return "Password must be at least 8 characters."
 return None
def token_response(user):
 access=create_access_token(identity=str(user.id)); refresh=create_refresh_token(identity=str(user.id)); return {"accessToken":access,"refreshToken":refresh,"user":user_payload(user)}

@app.get("/")
def service_root():
 return ok({"service":"Nexora API","status":"online","health":"/api/health"})

@app.get("/api/health")
def health():
 try:db.session.execute(db.text("SELECT 1"));return ok({"message":"Nexora API is running","database":"connected","environment":APP_ENV})
 except Exception as exc:db.session.rollback();logger.exception("Health check failed");return error("Database unavailable.",503,"DATABASE_UNAVAILABLE")
@app.post("/api/auth/register")
@limiter.limit("8 per minute")
def register():
 data=request.get_json(silent=True) or {}; name=clean_string(data.get("name"),100); email=clean_string(data.get("email"),255).lower(); password=str(data.get("password") or ""); workspace_name=clean_string(data.get("workspaceName") or f"{name}'s Workspace",160)
 if len(name)<2 or not EMAIL_RE.match(email):return error("Enter a valid name and email address.",400,"VALIDATION_ERROR")
 pe=validate_password(password)
 if pe:return error(pe,400,"WEAK_PASSWORD")
 if User.query.filter(func.lower(User.email)==email).first():return error("An account with this email already exists.",409,"EMAIL_EXISTS")
 user=User(name=name,email=email,password_hash=generate_password_hash(password,method="scrypt"),role="Admin");db.session.add(user);db.session.flush();workspace=Workspace(name=workspace_name,slug=slugify(workspace_name),owner_id=user.id);db.session.add(workspace);db.session.flush();db.session.add(Membership(workspace_id=workspace.id,user_id=user.id,role="Admin"));record_activity(user.id,"Created the workspace",workspace.name);db.session.commit();response=token_response(user);response["workspace"]={"id":workspace.id,"name":workspace.name,"slug":workspace.slug,"role":"Admin"};return ok(response,201)
@app.post("/api/auth/login")
@limiter.limit("10 per minute")
def login():
 data=request.get_json(silent=True) or {};email=clean_string(data.get("email"),255).lower();password=str(data.get("password") or "")
 try:
  user=User.query.filter(func.lower(User.email)==email).first()
  if not user or not check_password_hash(user.password_hash,password):return error("Invalid email or password.",401,"INVALID_CREDENTIALS")
  ensure_user_workspace(user);db.session.commit();response=token_response(user);workspace=workspace_for_user(user.id);response["workspace"]={"id":workspace.id,"name":workspace.name,"slug":workspace.slug,"role":membership_for(user.id).role};return ok(response)
 except Exception as exc:
  db.session.rollback(); logger.exception("Login failed for email=%s", email); return error("Login failed on the server.",500,"LOGIN_FAILED")
@app.get("/api/auth/me")
@jwt_required()
def me():
 user=db.session.get(User,int(get_jwt_identity()))
 if not user:return error("User not found.",404,"USER_NOT_FOUND")
 ensure_user_workspace(user);membership,workspace=current_workspace_context(user.id);db.session.commit();return ok({"user":user_payload(user),"workspace":{"id":workspace.id,"name":workspace.name,"slug":workspace.slug,"role":membership.role} if workspace else None})
@app.post("/api/auth/refresh")
@jwt_required(refresh=True)
def refresh():return ok({"accessToken":create_access_token(identity=get_jwt_identity())})
@app.get("/api/workspace")
@jwt_required()
def get_workspace():
 user_id=int(get_jwt_identity());workspace=ensure_user_workspace(db.session.get(User,user_id));db.session.commit();membership=membership_for(user_id,workspace.id);return ok({"workspace":{"id":workspace.id,"name":workspace.name,"slug":workspace.slug,"role":membership.role}})
@app.get("/api/team")
@jwt_required()
def get_team():
 membership,workspace=current_workspace_context(int(get_jwt_identity()))
 if not membership:return error("Workspace not found.",404,"WORKSPACE_NOT_FOUND")
 members=db.session.query(User,Membership).join(Membership,Membership.user_id==User.id).filter(Membership.workspace_id==workspace.id).order_by(Membership.created_at.asc()).all();return ok({"members":[{**user_payload(user),"role":membership.role,"joinedAt":membership.created_at.isoformat() if membership.created_at else None} for user,membership in members]})
@app.post("/api/team/invite")
@require_role("Admin","Manager")
def invite_member():
 data=request.get_json(silent=True) or {};email=clean_string(data.get("email"),255).lower();role=clean_string(data.get("role") or "Member",40)
 if not EMAIL_RE.match(email) or role not in ROLES:return error("A valid email and role are required.",400,"VALIDATION_ERROR")
 token=uuid.uuid4().hex+uuid.uuid4().hex;invitation=WorkspaceInvitation(workspace_id=g.workspace.id,email=email,role=role,token=token,expires_at=now_utc()+timedelta(days=7));db.session.add(invitation);existing=User.query.filter(func.lower(User.email)==email).first()
 if existing:notify(existing.id,"Workspace invitation",f"You have been invited to {g.workspace.name} as {role}. ","invite")
 record_activity(int(get_jwt_identity()),"Invited a workspace member",email);db.session.commit();return ok({"invitation":{"id":invitation.id,"email":email,"role":role,"token":token,"expiresAt":invitation.expires_at.isoformat()}},201)
@app.post("/api/team/accept")
@jwt_required()
def accept_invitation():
 token=clean_string((request.get_json(silent=True) or {}).get("token"),128);invitation=WorkspaceInvitation.query.filter_by(token=token).first()
 if not invitation or invitation.accepted_at or invitation.expires_at<now_utc():return error("This invitation is invalid or expired.",400,"INVITATION_INVALID")
 user_id=int(get_jwt_identity());user=db.session.get(User,user_id)
 if user.email.lower()!=invitation.email.lower():return error("This invitation was sent to a different email address.",403,"INVITATION_EMAIL_MISMATCH")
 if not Membership.query.filter_by(workspace_id=invitation.workspace_id,user_id=user_id).first():db.session.add(Membership(workspace_id=invitation.workspace_id,user_id=user_id,role=invitation.role))
 invitation.accepted_at=now_utc();record_activity(user_id,"Joined the workspace",str(invitation.workspace_id));db.session.commit();return ok({"message":"Invitation accepted.","workspace":{"id":invitation.workspace_id,"role":invitation.role}})
@app.post("/api/team/invite-link")
@require_role("Admin","Manager")
def invite_link():
 data=request.get_json(silent=True) or {};email=clean_string(data.get("email"),255).lower();role=clean_string(data.get("role") or "Member",40)
 if not EMAIL_RE.match(email) or role not in ROLES:return error("A valid email and role are required.",400,"VALIDATION_ERROR")
 invitation=WorkspaceInvitation.query.filter_by(workspace_id=g.workspace.id,email=email,accepted_at=None).order_by(WorkspaceInvitation.created_at.desc()).first()
 if invitation and invitation.expires_at>now_utc():invitation.role=role
 else:
  invitation=WorkspaceInvitation(workspace_id=g.workspace.id,email=email,role=role,token=uuid.uuid4().hex+uuid.uuid4().hex,expires_at=now_utc()+timedelta(days=7));db.session.add(invitation);db.session.flush()
 existing=User.query.filter(func.lower(User.email)==email).first()
 if existing:notify(existing.id,"Workspace invitation",f"You have been invited to {g.workspace.name} as {role}.","invite")
 record_activity(int(get_jwt_identity()),"Invited a workspace member",email);db.session.commit();base=os.getenv("FRONTEND_URL","https://nexora-ops.vercel.app").rstrip("/");return ok({"invitation":{"id":invitation.id,"email":invitation.email,"role":invitation.role,"expiresAt":invitation.expires_at.isoformat()},"invitationLink":f"{base}/invite/{invitation.token}"},201)
@app.get("/api/projects")
@jwt_required()
def get_projects():
 membership,workspace=current_workspace_context(int(get_jwt_identity()));ids=[x[0] for x in db.session.query(ProjectWorkspace.project_id).filter_by(workspace_id=workspace.id).all()] if workspace else [];projects=Project.query.filter(Project.id.in_(ids)).order_by(Project.created_at.desc()).all() if ids else [];return ok({"projects":[project_payload(p,workspace.id) for p in projects]})
@app.get("/api/tasks")
@jwt_required()
def get_tasks():
 membership,workspace=current_workspace_context(int(get_jwt_identity()));ids=[x[0] for x in db.session.query(ProjectWorkspace.project_id).filter_by(workspace_id=workspace.id).all()] if workspace else [];tasks=Task.query.filter(Task.project_id.in_(ids)).order_by(Task.created_at.desc()).all() if ids else [];return ok({"tasks":[task_payload(t) for t in tasks]})
@app.get("/api/dashboard/summary")
@jwt_required()
def dashboard_summary():
 membership,workspace=current_workspace_context(int(get_jwt_identity()));ids=[x[0] for x in db.session.query(ProjectWorkspace.project_id).filter_by(workspace_id=workspace.id).all()] if workspace else [];tasks=Task.query.filter(Task.project_id.in_(ids)).all() if ids else [];projects=Project.query.filter(Project.id.in_(ids)).order_by(Project.created_at.desc()).all() if ids else [];counts={s:sum(t.status==s for t in tasks) for s in TASK_STATUSES};return ok({"stats":{"projects":len(projects),"tasks":len(tasks),"completed":counts["Done"],"teamMembers":Membership.query.filter_by(workspace_id=workspace.id).count()},"taskBreakdown":{"done":counts["Done"],"inProgress":counts["In Progress"],"todo":counts["Todo"],"review":counts["Review"],"blocked":counts["Blocked"]},"projects":[project_payload(p,workspace.id) for p in projects[:6]],"activity":[]})
@app.get("/api/analytics")
@jwt_required()
def analytics():
 membership,workspace=current_workspace_context(int(get_jwt_identity()));ids=[x[0] for x in db.session.query(ProjectWorkspace.project_id).filter_by(workspace_id=workspace.id).all()] if workspace else [];tasks=Task.query.filter(Task.project_id.in_(ids)).all() if ids else [];projects=Project.query.filter(Project.id.in_(ids)).all() if ids else [];counts={s:sum(t.status==s for t in tasks) for s in TASK_STATUSES};priorities={p:sum(t.priority==p for t in tasks) for p in TASK_PRIORITIES};total=len(tasks);return ok({"overview":{"completionRate":round(counts["Done"]/total*100,1) if total else 0,"totalTasks":total,"completedTasks":counts["Done"],"overdueTasks":0,"activeProjects":sum(p.status=="Active" for p in projects),"teamMembers":Membership.query.filter_by(workspace_id=workspace.id).count()},"tasksByStatus":counts,"tasksByPriority":priorities,"projectPerformance":[project_payload(p,workspace.id) for p in projects]})
@app.get("/api/activity")
@jwt_required()
def get_activity():
 membership,workspace=current_workspace_context(int(get_jwt_identity()));activities=Activity.query.join(Membership,Membership.user_id==Activity.user_id).filter(Membership.workspace_id==workspace.id).order_by(Activity.created_at.desc()).limit(100).all() if membership else [];return ok({"activity":[activity_payload(a) for a in activities]})
@app.delete("/api/activity/<int:activity_id>")
@jwt_required()
def delete_activity(activity_id):
 user_id=int(get_jwt_identity());membership,workspace=current_workspace_context(user_id)
 if not membership or membership.role!="Admin":return error("Only Admins can delete activity.",403,"FORBIDDEN")
 activity=db.session.query(Activity).join(Membership,Membership.user_id==Activity.user_id).filter(Activity.id==activity_id,Membership.workspace_id==workspace.id).first()
 if not activity:return error("Activity not found.",404,"ACTIVITY_NOT_FOUND")
 db.session.delete(activity);db.session.commit();return ok({"message":"Activity deleted successfully."})
@app.get("/api/notifications")
@jwt_required()
def get_notifications():
 items=Notification.query.filter_by(user_id=int(get_jwt_identity())).order_by(Notification.created_at.desc()).limit(100).all();return ok({"notifications":[notification_payload(x) for x in items]})
@app.patch("/api/notifications/<int:notification_id>/read")
@jwt_required()
def mark_notification_read(notification_id):
 item=Notification.query.filter_by(id=notification_id,user_id=int(get_jwt_identity())).first()
 if not item:return error("Notification not found.",404,"NOTIFICATION_NOT_FOUND")
 item.read_at=now_utc();db.session.commit();return ok({"message":"Notification marked as read."})
@app.before_request
def before_request():g.request_id=request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
@app.after_request
def after_request(response):response.headers["X-Request-ID"]=g.request_id;return response
@app.errorhandler(404)
def not_found(_):return error("Route not found.",404,"NOT_FOUND")
@app.errorhandler(500)
def internal(_):db.session.rollback();logger.exception("Unhandled request exception");return error("Internal server error.",500,"INTERNAL_ERROR")
with app.app_context():db.create_all()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")),debug=APP_ENV!="production")
