"""Initialize Nexora database tables before the web server starts."""

from app import app, db


with app.app_context():
    db.create_all()
    print("Nexora database tables are ready.")
