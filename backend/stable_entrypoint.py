from app import app
import app as app_module
import app_extra

# Use the stable workspace-aware runtime.
app_module.membership_for = lambda user_id, workspace_id=None: (
    app_extra.workspace_user(user_id, workspace_id)
    if workspace_id is not None
    else app_extra.selected_membership(user_id)
)
app_module.current_workspace_context = app_extra.selected_workspace

for endpoint, handler in {
    "get_workspace": app_extra.get_selected_workspace_extra,
    "get_team": app_extra.get_team_extra,
    "get_projects": app_extra.get_projects_extra,
    "get_tasks": app_extra.get_tasks_extra,
    "accept_invitation": app_extra.accept_invitation_extra,
}.items():
    app.view_functions[endpoint] = handler
