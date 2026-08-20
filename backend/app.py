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
from flask_jwt_extended import (JWTManager, create_access_token, create_refresh_token, get_jwt, get_jwt_identity, jwt_required)
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
if IS_PRODUCTION and (not SECRET_KEY or SECRET_KEY == "change-this-in-production"): raise RuntimeError("SECRET_KEY must be configured in production.")
if IS_PRODUCTION and (not JWT_SECRET_KEY or JWT_SECRET_KEY == "change-this-jwt-secret-in-production"): raise RuntimeError("JWT_SECRET_KEY must be configured in production.")
if DATABASE_URL.startswith("postgres://"): DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"): DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s")
logger = logging.getLogger("nexora.api")
db = SQLAlchemy()
jwt = JWTManager()
app = Flask(__name__)
app.config.update(SECRET_KEY=SECRET_KEY or "dev-only-secret", JWT_SECRET_KEY=JWT_SECRET_KEY or "dev-only-jwt-secret", JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30"))), JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "30"))), SQLALCHEMY_DATABASE_URI=DATABASE_URL, SQLALCHEMY_TRACK_MODIFICATIONS=False, SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True}, MAX_CONTENT_LENGTH=1024 * 1024)
db.init_app(app)
jwt.init_app(app)
# Authentication is bearer-token based, so wildcard CORS is safe here and avoids
# breaking the API when Vercel changes the deployment hostname.
CORS(app, resources={r"/api/*": {"origins": "*"}}, allow_headers=["Content-Type", "Authorization", "X-Request-ID"], methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
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
    __tablename__="project_members"; id=db.Column(db.Integer,primary_key=True); project_id=db.Column(db.Integer,db.ForeignKey("project.id",ondelete="CASCADE"),nullable=False,index=True); user_id=db.Column(db.Integer,db.ForeignKey("user.id",ondelete="CASCADE"),nullable=False,index=True); created_at=db.Column(db.DateTime,server_default=db.func.now(),index=True); __table_args__=(UniqueConstraint("project_id","user_id",name="uq_project_member"),)
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
def record_activity(user_id,action,context="",workspace_id=None): db.session.add(Activity(user_id=user_id,action=action,context=context))
def notify(user_id,title,message,kind="info"):
    if user_id: db.session.add(Notification(user_id=user_id,title=title,message=message,kind=kind))
def token_response(user): return {"accessToken":create_access_token(identity=str(user.id)),"refreshToken":create_refresh_token(identity=str(user.id)),"user":user_payload(user)}
def validate_password(password):
    if len(password)<8:return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]",password) or not re.search(r"\d",password):return "Password must contain at least one letter and one number."
    return None

@app.before_request
def start_request(): g.request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4()); g.request_started=time.perf_counter()
@app.after_request
def finish_request(response): response.headers["X-Request-ID"]=getattr(g,"request_id","-"); response.headers["X-Content-Type-Options"]="nosniff"; response.headers["X-Frame-Options"]="DENY"; response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"; return response
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

# Auth and workspace routes remain in the existing app.py below this point.
