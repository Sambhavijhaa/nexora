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
logging.basicConfig(level=getattr(logging,os.getenv("LOG_LEVEL","INFO").upper(),logging.INFO),format="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s")
logger=logging.getLogger("nexora.api"); db=SQLAlchemy(); jwt=JWTManager(); app=Flask(__name__)
app.config.update(SECRET_KEY=SECRET_KEY or "dev-only-secret",JWT_SECRET_KEY=JWT_SECRET_KEY or "dev-only-jwt-secret",JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES","30"))),JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=int(os.getenv("JWT_REFRESH_DAYS","30"))),SQLALCHEMY_DATABASE_URI=DATABASE_URL,SQLALCHEMY_TRACK_MODIFICATIONS=False,SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping":True},MAX_CONTENT_LENGTH=1024*1024)
db.init_app(app); jwt.init_app(app)
configured_origins=[x.strip() for x in os.getenv("CORS_ORIGINS","").split(",") if x.strip()]
if IS_PRODUCTION and not configured_origins: configured_origins=["https://nexora-ops.vercel.app"]
CORS(app,resources={r"/api/*":{"origins":configured_origins or "*"}},allow_headers=["Content-Type","Authorization","X-Request-ID"],methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"])
limiter=Limiter(key_func=get_remote_address,app=app,default_limits=["300 per minute"],storage_uri=os.getenv("RATELIMIT_STORAGE_URI","memory://"),headers_enabled=True)
EMAIL_RE=re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$"); ROLES={"Admin","Manager","Member","Viewer"}; TASK_STATUSES={"Todo","In Progress","Review","Done","Blocked"}; TASK_PRIORITIES={"Low","Medium","High","Critical"}
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
 p={"success":False,"message":message};
 if code:p["errorCode"]=code
 if details:p["details"]=details
 p["requestId"]=getattr(g,"request_id",None); return jsonify(p),status
def ok(payload=None,status=200):
 p={"success":True};
 if payload:p.update(payload)
 return jsonify(p),status
def clean_string(value,max_len=500): return str(value or "").strip()[:max_len]
def slugify(value):
 s=re.sub(r"[^a-z0-9]+","-",clean_string(value,120).lower()).strip("-") or "workspace"; base=s; n=2
 while Workspace.query.filter_by(slug=s).first(): s=f"{base}-{n}"; n+=1
 return s
def user_payload(u): return {"id":u.id,"name":u.name,"email":u.email,"role":u.role}
def workspace_for_user(uid):
 m=Membership.query.filter_by(user_id=uid).order_by(Membership.created_at.asc()).first(); return Workspace.query.get(m.workspace_id) if m else None
def membership_for(uid,wid=None):
 if not wid:
  w=workspace_for_user(uid); wid=w.id if w else None
 return Membership.query.filter_by(workspace_id=wid,user_id=uid).first() if wid else None
def current_workspace_context(uid=None):
 uid=uid or int(get_jwt_identity()); m=membership_for(uid); return m,Workspace.query.get(m.workspace_id) if m else None
def require_role(*roles):
 def dec(fn):
  @wraps(fn)
  @jwt_required()
  def wrapped(*a,**kw):
   m=membership_for(int(get_jwt_identity()))
   if not m:return error("You are not a member of a workspace.",403,"WORKSPACE_ACCESS_DENIED")
   if m.role not in roles:return error("You do not have permission to perform this action.",403,"FORBIDDEN")
   g.membership=m; g.workspace=Workspace.query.get(m.workspace_id); return fn(*a,**kw)
  return wrapped
 return dec
def ensure_user_workspace(u):
 m=Membership.query.filter_by(user_id=u.id).first()
 if m:return Workspace.query.get(m.workspace_id)
 w=Workspace(name=f"{u.name}'s Workspace",slug=slugify(f"{u.name}-workspace"),owner_id=u.id); db.session.add(w); db.session.flush(); db.session.add(Membership(workspace_id=w.id,user_id=u.id,role="Admin")); return w
def record_activity(uid,action,context=""): db.session.add(Activity(user_id=uid,action=action,context=context))
def notify(uid,title,message,kind="info"): db.session.add(Notification(user_id=uid,title=title,message=message,kind=kind))
def project_payload(p,wid=None): return {"id":p.id,"name":p.name,"description":p.description or "","status":p.status,"progress":p.progress,"workspaceId":wid,"memberCount":ProjectMember.query.filter_by(project_id=p.id).count(),"createdAt":p.created_at.isoformat() if p.created_at else None}
def task_payload(t):
 m=TaskMeta.query.filter_by(task_id=t.id).first(); a=db.session.get(User,t.assignee_id) if t.assignee_id else None; return {"id":t.id,"title":t.title,"description":t.description or "","status":t.status,"priority":t.priority,"projectId":t.project_id,"projectName":t.project.name if t.project else "","assignee":user_payload(a) if a else None,"dueDate":m.due_date.isoformat() if m and m.due_date else None,"labels":[x for x in (m.labels.split(",") if m and m.labels else []) if x],"createdAt":t.created_at.isoformat() if t.created_at else None}
def activity_payload(a): return {"id":a.id,"action":a.action,"context":a.context or "","user":user_payload(a.user) if a.user else None,"createdAt":a.created_at.isoformat() if a.created_at else None}
def notification_payload(n): return {"id":n.id,"title":n.title,"message":n.message,"kind":n.kind,"read":bool(n.read_at),"createdAt":n.created_at.isoformat() if n.created_at else None}
def validate_password(p): return "Password must be at least 8 characters." if len(p)<8 else None
def token_response(u): return {"accessToken":create_access_token(identity=str(u.id)),"refreshToken":create_refresh_token(identity=str(u.id)),"user":user_payload(u)}
@app.get("/api/health")
def health(): return ok({"message":"Nexora API is running","database":"connected","environment":APP_ENV})
@app.post("/api/auth/register")
def register():
 d=request.get_json(silent=True) or {}; name=clean_string(d.get("name"),100); email=clean_string(d.get("email"),255).lower(); pw=str(d.get("password") or "")
 if len(name)<2 or not EMAIL_RE.match(email):return error("Enter a valid name and email address.",400,"VALIDATION_ERROR")
 if validate_password(pw):return error(validate_password(pw),400,"WEAK_PASSWORD")
 if User.query.filter(func.lower(User.email)==email).first():return error("An account with this email already exists.",409,"EMAIL_EXISTS")
 u=User(name=name,email=email,password_hash=generate_password_hash(pw,method="scrypt"),role="Admin"); db.session.add(u); db.session.flush(); wname=clean_string(d.get("workspaceName") or f"{name}'s Workspace",160); w=Workspace(name=wname,slug=slugify(wname),owner_id=u.id); db.session.add(w); db.session.flush(); db.session.add(Membership(workspace_id=w.id,user_id=u.id,role="Admin")); record_activity(u.id,"Created the workspace",w.name); db.session.commit(); r=token_response(u); r["workspace"]={"id":w.id,"name":w.name,"slug":w.slug,"role":"Admin"}; return ok(r,201)
@app.post("/api/auth/login")
def login():
 d=request.get_json(silent=True) or {}; email=clean_string(d.get("email"),255).lower(); pw=str(d.get("password") or ""); u=User.query.filter(func.lower(User.email)==email).first()
 if not u or not check_password_hash(u.password_hash,pw):return error("Invalid email or password.",401,"INVALID_CREDENTIALS")
 ensure_user_workspace(u); db.session.commit(); r=token_response(u); w=workspace_for_user(u.id); r["workspace"]={"id":w.id,"name":w.name,"slug":w.slug,"role":membership_for(u.id).role}; return ok(r)
@app.post("/api/auth/refresh")
@jwt_required(refresh=True)
def refresh(): return ok({"accessToken":create_access_token(identity=str(int(get_jwt_identity())))})
@app.get("/api/auth/me")
@jwt_required()
def me():
 u=db.session.get(User,int(get_jwt_identity()));
 if not u:return error("User not found.",404,"USER_NOT_FOUND")
 ensure_user_workspace(u); m,w=current_workspace_context(u.id); db.session.commit(); return ok({"user":user_payload(u),"workspace":{"id":w.id,"name":w.name,"slug":w.slug,"role":m.role}})
@app.get("/api/workspace")
@jwt_required()
def get_workspace():
 uid=int(get_jwt_identity()); w=ensure_user_workspace(db.session.get(User,uid)); db.session.commit(); m=membership_for(uid,w.id); return ok({"workspace":{"id":w.id,"name":w.name,"slug":w.slug,"role":m.role}})
@app.get("/api/team")
@jwt_required()
def get_team():
 m,w=current_workspace_context(int(get_jwt_identity())); rows=db.session.query(User,Membership).join(Membership,Membership.user_id==User.id).filter(Membership.workspace_id==w.id).order_by(Membership.created_at.asc()).all(); return ok({"members":[{**user_payload(u),"role":mm.role,"joinedAt":mm.created_at.isoformat() if mm.created_at else None} for u,mm in rows]})
@app.post("/api/team/invite")
@require_role("Admin","Manager")
def invite_member():
 d=request.get_json(silent=True) or {}; email=clean_string(d.get("email"),255).lower(); role=clean_string(d.get("role") or "Member",40)
 if not EMAIL_RE.match(email) or role not in ROLES:return error("A valid email and role are required.",400,"VALIDATION_ERROR")
 token=uuid.uuid4().hex+uuid.uuid4().hex; inv=WorkspaceInvitation(workspace_id=g.workspace.id,email=email,role=role,token=token,expires_at=now_utc()+timedelta(days=7)); db.session.add(inv); existing=User.query.filter(func.lower(User.email)==email).first()
 if existing:notify(existing.id,"Workspace invitation",f"You have been invited to {g.workspace.name} as {role}.","invite")
 record_activity(int(get_jwt_identity()),"Invited a workspace member",email); db.session.commit(); return ok({"invitation":{"id":inv.id,"email":email,"role":role,"token":token,"expiresAt":inv.expires_at.isoformat()}},201)
@app.post("/api/team/accept")
@jwt_required()
def accept_invitation():
 token=clean_string((request.get_json(silent=True) or {}).get("token"),128); inv=WorkspaceInvitation.query.filter_by(token=token).first()
 if not inv or inv.accepted_at or inv.expires_at<now_utc():return error("This invitation is invalid or expired.",400,"INVITATION_INVALID")
 uid=int(get_jwt_identity()); u=db.session.get(User,uid)
 if u.email.lower()!=inv.email.lower():return error("This invitation was sent to a different email address.",403,"INVITATION_EMAIL_MISMATCH")
 if not Membership.query.filter_by(workspace_id=inv.workspace_id,user_id=uid).first():db.session.add(Membership(workspace_id=inv.workspace_id,user_id=uid,role=inv.role))
 inv.accepted_at=now_utc(); record_activity(uid,"Joined the workspace",str(inv.workspace_id)); db.session.commit(); return ok({"message":"Invitation accepted."})
@app.get("/api/projects")
@jwt_required()
def get_projects():
 m,w=current_workspace_context(int(get_jwt_identity())); ids=[x[0] for x in db.session.query(ProjectWorkspace.project_id).filter_by(workspace_id=w.id).all()]; rows=Project.query.filter(Project.id.in_(ids)).order_by(Project.created_at.desc()).all() if ids else []; return ok({"projects":[project_payload(x,w.id) for x in rows]})
@app.get("/api/tasks")
@jwt_required()
def get_tasks():
 m,w=current_workspace_context(int(get_jwt_identity())); ids=[x[0] for x in db.session.query(ProjectWorkspace.project_id).filter_by(workspace_id=w.id).all()]; rows=Task.query.filter(Task.project_id.in_(ids)).order_by(Task.created_at.desc()).all() if ids else []; return ok({"tasks":[task_payload(x) for x in rows]})
@app.get("/api/dashboard/summary")
@jwt_required()
def dashboard_summary():
 m,w=current_workspace_context(int(get_jwt_identity())); ids=[x[0] for x in db.session.query(ProjectWorkspace.project_id).filter_by(workspace_id=w.id).all()]; ts=Task.query.filter(Task.project_id.in_(ids)).all() if ids else []; ps=Project.query.filter(Project.id.in_(ids)).order_by(Project.created_at.desc()).all() if ids else []; c={s:sum(t.status==s for t in ts) for s in TASK_STATUSES}; return ok({"stats":{"projects":len(ps),"tasks":len(ts),"completed":c["Done"],"teamMembers":Membership.query.filter_by(workspace_id=w.id).count()},"taskBreakdown":{"done":c["Done"],"inProgress":c["In Progress"],"todo":c["Todo"],"review":c["Review"],"blocked":c["Blocked"]},"projects":[project_payload(p,w.id) for p in ps[:6]],"activity":[]})
@app.get("/api/analytics")
@jwt_required()
def analytics():
 m,w=current_workspace_context(int(get_jwt_identity())); ids=[x[0] for x in db.session.query(ProjectWorkspace.project_id).filter_by(workspace_id=w.id).all()]; ts=Task.query.filter(Task.project_id.in_(ids)).all() if ids else []; c={s:sum(t.status==s for t in ts) for s in TASK_STATUSES}; total=len(ts); return ok({"overview":{"completionRate":round(c["Done"]/total*100,1) if total else 0,"totalTasks":total,"completedTasks":c["Done"]},"tasksByStatus":c})
@app.get("/api/activity")
@jwt_required()
def activity():
 m,w=current_workspace_context(int(get_jwt_identity())); rows=Activity.query.join(Membership,Membership.user_id==Activity.user_id).filter(Membership.workspace_id==w.id).order_by(Activity.created_at.desc()).limit(100).all(); return ok({"activity":[activity_payload(a) for a in rows]})
@app.delete("/api/activity/<int:activity_id>")
@jwt_required()
def delete_activity(activity_id):
 uid=int(get_jwt_identity());m,w=current_workspace_context(uid)
 if not m or m.role!="Admin":return error("Only Admins can delete activity.",403,"FORBIDDEN")
 a=db.session.query(Activity).join(Membership,Membership.user_id==Activity.user_id).filter(Activity.id==activity_id,Membership.workspace_id==w.id).first()
 if not a:return error("Activity not found.",404,"ACTIVITY_NOT_FOUND")
 db.session.delete(a);db.session.commit();return ok({"message":"Activity deleted successfully."})
@app.get("/api/notifications")
@jwt_required()
def notifications():
 rows=Notification.query.filter_by(user_id=int(get_jwt_identity())).order_by(Notification.created_at.desc()).limit(100).all();return ok({"notifications":[notification_payload(n) for n in rows]})
@app.before_request
def before_request():g.request_id=request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
@app.after_request
def after_request(response):response.headers["X-Request-ID"]=g.request_id;return response
with app.app_context():db.create_all()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")),debug=APP_ENV!="production")
