import logging
import os
import time
import uuid
from collections import defaultdict
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()


def configure_logging():
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s",
    )


configure_logging()
logger = logging.getLogger("nexora.api")
db = SQLAlchemy()
app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-me-jwt")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30")))
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "30")))

database_url = os.getenv("DATABASE_URL", "sqlite:///nexora.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

cors_origins = os.getenv("CORS_ORIGINS", "*")
CORS(app, resources={r"/*": {"origins": cors_origins.split(",") if cors_origins != "*" else "*"}})
db.init_app(app)
jwt = JWTManager(app)

# Lightweight process-local rate limiter for auth endpoints. Production deployments
# can replace this with Redis without changing the API contract.
_rate_window = 60
_rate_limit = 30
_rate_hits = defaultdict(list)


@app.before_request
def start_request():
    g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    g.request_started = time.perf_counter()
    if request.path.startswith("/api/auth/"):
        now = time.time()
        bucket = [t for t in _rate_hits[request.remote_addr] if now - t < _rate_window]
        bucket.append(now)
        _rate_hits[request.remote_addr] = bucket
        if len(bucket) > _rate_limit:
            return jsonify({"success": False, "message": "Too many authentication requests. Try again shortly."}), 429


@app.after_request
def log_request(response):
    duration_ms = round((time.perf_counter() - getattr(g, "request_started", time.perf_counter())) * 1000, 2)
    logger.info(
        "%s %s status=%s duration_ms=%s",
        request.method,
        request.path,
        response.status_code,
        duration_ms,
        extra={"request_id": getattr(g, "request_id", "-")},
    )
    response.headers["X-Request-ID"] = getattr(g, "request_id", "-")
    return response


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    logger.exception("Unhandled application error", extra={"request_id": getattr(g, "request_id", "-")})
    db.session.rollback()
    return jsonify({"success": False, "message": "Internal server error.", "requestId": getattr(g, "request_id", None)}), 500


@jwt.unauthorized_loader
def jwt_missing(reason):
    return jsonify({"success": False, "message": "Authorization token is required."}), 401


@jwt.invalid_token_loader
def jwt_invalid(reason):
    return jsonify({"success": False, "message": "Invalid authorization token."}), 401


@jwt.expired_token_loader
def jwt_expired(header, payload):
    return jsonify({"success": False, "message": "Token expired."}), 401


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(40), nullable=False, default="Member")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    projects = db.relationship("Project", backref="owner", lazy=True, cascade="all, delete-orphan")


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(40), nullable=False, default="Active")
    progress = db.Column(db.Integer, nullable=False, default=0)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    tasks = db.relationship("Task", backref="project", lazy=True, cascade="all, delete-orphan")


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(40), nullable=False, default="Todo")
    priority = db.Column(db.String(30), nullable=False, default="Medium")
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False, index=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    action = db.Column(db.String(180), nullable=False)
    context = db.Column(db.String(180), default="")
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)


def user_payload(user):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


def project_payload(project):
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description or "",
        "status": project.status,
        "progress": project.progress,
        "createdAt": project.created_at.isoformat() if project.created_at else None,
    }


def task_payload(task):
    assignee = db.session.get(User, task.assignee_id) if task.assignee_id else None
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description or "",
        "status": task.status,
        "priority": task.priority,
        "projectId": task.project_id,
        "projectName": task.project.name if task.project else "",
        "assignee": user_payload(assignee) if assignee else None,
        "createdAt": task.created_at.isoformat() if task.created_at else None,
    }


def token_response(user):
    return {
        "success": True,
        "accessToken": create_access_token(identity=str(user.id)),
        "refreshToken": create_refresh_token(identity=str(user.id)),
        "user": user_payload(user),
    }


def record_activity(user_id, action, context=""):
    db.session.add(Activity(user_id=user_id, action=action, context=context))


@app.get("/")
def root():
    return jsonify({"success": True, "message": "Nexora API is running", "health": "/api/health", "api": "/api"})


@app.get("/api")
@app.get("/api/")
def api_root():
    return jsonify({
        "success": True,
        "message": "Nexora API is running",
        "health": "/api/health",
        "endpoints": [
            "/api/auth/register", "/api/auth/login", "/api/auth/refresh", "/api/auth/me",
            "/api/dashboard/summary", "/api/projects", "/api/tasks", "/api/team", "/api/activity",
        ],
    })


@app.get("/api/health")
@app.get("/api/health/")
def health():
    database = "connected"
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception:
        db.session.rollback()
        database = "unavailable"
    status_code = 200 if database == "connected" else 503
    return jsonify({"success": database == "connected", "message": "Nexora API is running", "database": database}), status_code


@app.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if not name or not email or len(password) < 8:
        return jsonify({"success": False, "message": "Name, email and an 8-character password are required."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "An account with this email already exists."}), 409
    user = User(name=name, email=email, password_hash=generate_password_hash(password), role="Admin")
    db.session.add(user)
    db.session.flush()
    record_activity(user.id, "Created the workspace", "Workspace")
    db.session.commit()
    return jsonify(token_response(user)), 201


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401
    return jsonify(token_response(user))


@app.post("/api/auth/refresh")
@jwt_required(refresh=True)
def refresh():
    return jsonify({"success": True, "accessToken": create_access_token(identity=get_jwt_identity())})


@app.post("/api/auth/logout")
@jwt_required(refresh=True)
def logout():
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.get("/api/auth/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
    return jsonify({"success": True, "user": user_payload(user)})


@app.get("/api/dashboard/summary")
@jwt_required()
def dashboard_summary():
    owner_id = int(get_jwt_identity())
    projects = Project.query.filter_by(owner_id=owner_id).all()
    project_ids = [p.id for p in projects]
    tasks = Task.query.filter(Task.project_id.in_(project_ids)).all() if project_ids else []
    completed = sum(1 for t in tasks if t.status == "Done")
    in_progress = sum(1 for t in tasks if t.status == "In Progress")
    todo = sum(1 for t in tasks if t.status == "Todo")
    activities = Activity.query.filter_by(user_id=owner_id).order_by(Activity.created_at.desc()).limit(8).all()
    return jsonify({
        "success": True,
        "stats": {
            "projects": len(projects),
            "tasks": len(tasks),
            "completed": completed,
            "teamMembers": User.query.count(),
        },
        "taskBreakdown": {"done": completed, "inProgress": in_progress, "todo": todo},
        "projects": [project_payload(p) for p in projects[:6]],
        "activity": [
            {"id": a.id, "action": a.action, "context": a.context, "createdAt": a.created_at.isoformat() if a.created_at else None}
            for a in activities
        ],
    })


@app.get("/api/projects")
@jwt_required()
def get_projects():
    owner_id = int(get_jwt_identity())
    projects = Project.query.filter_by(owner_id=owner_id).order_by(Project.created_at.desc()).all()
    return jsonify({"success": True, "projects": [project_payload(p) for p in projects]})


@app.post("/api/projects")
@jwt_required()
def create_project():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"success": False, "message": "Project name is required."}), 400
    project = Project(
        name=name,
        description=str(data.get("description", "")).strip(),
        status=str(data.get("status", "Active")),
        progress=max(0, min(100, int(data.get("progress", 0) or 0))),
        owner_id=int(get_jwt_identity()),
    )
    db.session.add(project)
    db.session.flush()
    record_activity(project.owner_id, "Created a project", project.name)
    db.session.commit()
    return jsonify({"success": True, "project": project_payload(project)}), 201


@app.delete("/api/projects/<int:project_id>")
@jwt_required()
def delete_project(project_id):
    owner_id = int(get_jwt_identity())
    project = Project.query.filter_by(id=project_id, owner_id=owner_id).first()
    if not project:
        return jsonify({"success": False, "message": "Project not found."}), 404
    record_activity(owner_id, "Deleted a project", project.name)
    db.session.delete(project)
    db.session.commit()
    return jsonify({"success": True})


@app.get("/api/tasks")
@jwt_required()
def get_tasks():
    owner_id = int(get_jwt_identity())
    tasks = Task.query.join(Project).filter(Project.owner_id == owner_id).order_by(Task.created_at.desc()).all()
    return jsonify({"success": True, "tasks": [task_payload(t) for t in tasks]})


@app.post("/api/tasks")
@jwt_required()
def create_task():
    owner_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    project_id = data.get("projectId")
    if not title or not project_id:
        return jsonify({"success": False, "message": "Task title and project are required."}), 400
    project = Project.query.filter_by(id=int(project_id), owner_id=owner_id).first()
    if not project:
        return jsonify({"success": False, "message": "Project not found."}), 404
    task = Task(
        title=title,
        description=str(data.get("description", "")).strip(),
        status=str(data.get("status", "Todo")),
        priority=str(data.get("priority", "Medium")),
        project_id=project.id,
        assignee_id=int(data["assigneeId"]) if data.get("assigneeId") else None,
    )
    db.session.add(task)
    db.session.flush()
    record_activity(owner_id, "Created a task", task.title)
    db.session.commit()
    return jsonify({"success": True, "task": task_payload(task)}), 201


@app.patch("/api/tasks/<int:task_id>")
@jwt_required()
def update_task(task_id):
    owner_id = int(get_jwt_identity())
    task = Task.query.join(Project).filter(Task.id == task_id, Project.owner_id == owner_id).first()
    if not task:
        return jsonify({"success": False, "message": "Task not found."}), 404
    data = request.get_json(silent=True) or {}
    if "status" in data:
        task.status = str(data["status"])
    if "priority" in data:
        task.priority = str(data["priority"])
    if "title" in data and str(data["title"]).strip():
        task.title = str(data["title"]).strip()
    record_activity(owner_id, "Updated a task", task.title)
    db.session.commit()
    return jsonify({"success": True, "task": task_payload(task)})


@app.delete("/api/tasks/<int:task_id>")
@jwt_required()
def delete_task(task_id):
    owner_id = int(get_jwt_identity())
    task = Task.query.join(Project).filter(Task.id == task_id, Project.owner_id == owner_id).first()
    if not task:
        return jsonify({"success": False, "message": "Task not found."}), 404
    record_activity(owner_id, "Deleted a task", task.title)
    db.session.delete(task)
    db.session.commit()
    return jsonify({"success": True})


@app.get("/api/team")
@jwt_required()
def get_team():
    users = User.query.order_by(User.created_at.asc()).all()
    return jsonify({"success": True, "members": [user_payload(u) for u in users]})


@app.get("/api/activity")
@jwt_required()
def get_activity():
    owner_id = int(get_jwt_identity())
    activities = Activity.query.filter_by(user_id=owner_id).order_by(Activity.created_at.desc()).limit(50).all()
    return jsonify({"success": True, "activity": [
        {"id": a.id, "action": a.action, "context": a.context, "createdAt": a.created_at.isoformat() if a.created_at else None}
        for a in activities
    ]})


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
