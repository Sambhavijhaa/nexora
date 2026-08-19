"""Small startup extension for the deployed Nexora API.

Python loads sitecustomize automatically when this directory is on sys.path.
It registers the Admin-only Activity deletion endpoint without changing the
existing app.py code or database schema.
"""

try:
    from flask_jwt_extended import get_jwt_identity
    from app import Activity, Membership, app, current_workspace_context, db, error, ok, require_role

    if "/api/activity/<int:activity_id>" not in {str(rule) for rule in app.url_map.iter_rules()}:
        @app.delete("/api/activity/<int:activity_id>")
        @require_role("Admin")
        def delete_activity(activity_id):
            user_id = int(get_jwt_identity())
            membership, workspace = current_workspace_context(user_id)
            if not membership or not workspace:
                return error("Workspace not found.", 404, "WORKSPACE_NOT_FOUND")

            activity = db.session.get(Activity, activity_id)
            if not activity:
                return error("Activity not found.", 404, "ACTIVITY_NOT_FOUND")

            belongs_to_workspace = Membership.query.filter_by(
                workspace_id=workspace.id,
                user_id=activity.user_id,
            ).first()
            if not belongs_to_workspace:
                return error("Activity not found.", 404, "ACTIVITY_NOT_FOUND")

            db.session.delete(activity)
            db.session.commit()
            return ok({"message": "Activity deleted."})
except Exception:
    # Never prevent the main API from starting if the optional extension fails.
    pass
