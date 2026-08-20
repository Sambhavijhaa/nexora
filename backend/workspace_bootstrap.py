from app import app

# Render's declarative start command uses this module so the stable
# workspace runtime is loaded after the Flask application is initialized.
import runtime_v2  # noqa: F401

app = app
