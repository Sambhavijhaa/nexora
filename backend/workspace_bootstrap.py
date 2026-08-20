from app import app

# Render's declarative start command may load workspace_bootstrap:app instead
# of app:app. Import the same runtime extensions in that case.
import runtime_extensions  # noqa: F401

# Re-export the already initialized Flask application.
app = app
