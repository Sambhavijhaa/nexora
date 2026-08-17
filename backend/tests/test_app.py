import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"

from app import app, db  # noqa: E402


def setup_function():
    app.config.update(TESTING=True)
    with app.app_context():
        db.drop_all()
        db.create_all()


def teardown_function():
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_root_and_health():
    client = app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/api/health").status_code == 200


def test_register_login_refresh_and_me():
    client = app.test_client()
    register = client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": "test@example.com", "password": "password123"},
    )
    assert register.status_code == 201
    body = register.get_json()
    assert body["accessToken"]
    assert body["refreshToken"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['accessToken']}"})
    assert me.status_code == 200
    assert me.get_json()["user"]["email"] == "test@example.com"

    refresh = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {body['refreshToken']}"},
    )
    assert refresh.status_code == 200
    assert refresh.get_json()["accessToken"]


def test_protected_projects_require_auth():
    client = app.test_client()
    response = client.get("/api/projects")
    assert response.status_code == 401
