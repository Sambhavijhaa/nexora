from flask_jwt_extended import get_jwt_identity

from app import Activity, Membership, app, current_workspace_context, db, error, ok, require_role


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

    # Activity belongs to a workspace through the user who generated it.
    # Only allow deletion when that user is a member of the current workspace.
    belongs_to_workspace = Membership.query.filter_by(
        workspace_id=workspace.id,
        user_id=activity.user_id,
    ).first()
    if not belongs_to_workspace:
        return error("Activity not found.", 404, "ACTIVITY_NOT_FOUND")

    db.session.delete(activity)
    db.session.commit()
    return ok({"message": "Activity deleted."})
