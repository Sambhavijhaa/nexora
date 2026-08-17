import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

db = SQLAlchemy()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "nexora-dev-secret")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "nexora-dev-jwt-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=8)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///nexora.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

CORS(app, resources={r"/api/*": {"origins": "*"}})
db.init_app(app)
JWTManager(app)


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


@app.get("/")
def root():
    return jsonify({"success": True, "message": "Nexora API is running", "health": "/api/health"})


@app.get("/api/health")
def health():
    return {"success": True, "message": "Nexora API is running"}


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
    token = create_access_token(identity=str(user.id))
    return jsonify({"success": True, "token": token, "user": user_payload(user)}), 201


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"success": True, "token": token, "user": user_payload(user)})


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

    project = Project(
        name=name,
        description=str(data.get("description", "")).strip(),
        status=str(data.get("status", "Active")),
        progress=max(0, min(100, int(data.get("progress", 0)))),
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
    app.run(debug=True, port=5000)
