import logging
import os
import time
import uuid
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    get_jwt,
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

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "nexora-dev-secret")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "nexora-dev-jwt-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30")))
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "30")))

# Render/Postgres may provide postgres:// or postgresql://. SQLAlchemy uses the
# psycopg driver explicitly in production.
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


@app.before_request
def start_request():
    g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    g.request_started = time.perf_counter()


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
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


def user_payload(user):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


def project_payload(project):
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "progress": project.progress,
        "createdAt": project.created_at.isoformat() if project.created_at else None,
    }


def token_response(user):
    return {
        "success": True,
        "accessToken": create_access_token(identity=str(user.id)),
        "refreshToken": create_refresh_token(identity=str(user.id)),
        "user": user_payload(user),
    }


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
        "endpoints": ["/api/auth/register", "/api/auth/login", "/api/auth/refresh", "/api/auth/me", "/api/projects"],
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
    identity = get_jwt_identity()
    return jsonify({"success": True, "accessToken": create_access_token(identity=identity)})


@app.post("/api/auth/logout")
@jwt_required(refresh=True)
def logout():
    # Stateless JWT logout: the client must discard both tokens. A future
    # Redis-backed blocklist can revoke refresh-token JTIs when required.
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.get("/api/auth/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
    return jsonify({"success": True, "user": user_payload(user)})


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
    try:
        progress = int(data.get("progress", 0))
    except (TypeError, ValueError):
        progress = 0
    project = Project(
        name=name,
        description=str(data.get("description", "")).strip(),
        status=str(data.get("status", "Active")),
        progress=max(0, min(100, progress)),
        owner_id=int(get_jwt_identity()),
    )
    db.session.add(project)
    db.session.commit()
    return jsonify({"success": True, "project": project_payload(project)}), 201


@app.delete("/api/projects/<int:project_id>")
@jwt_required()
def delete_project(project_id):
    project = Project.query.filter_by(id=project_id, owner_id=int(get_jwt_identity())).first()
    if not project:
        return jsonify({"success": False, "message": "Project not found."}), 404
    db.session.delete(project)
    db.session.commit()
    return jsonify({"success": True})


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
