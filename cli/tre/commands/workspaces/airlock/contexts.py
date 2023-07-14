import click
from tre.commands.workspaces.contexts import WorkspaceContext


class WorkspaceAirlockContext(object):
    def __init__(self, workspace_id: str, airlock_request_id: str):
        self.workspace_id = workspace_id
        self.airlock_request_id = airlock_request_id

    @staticmethod
    def add_airlock_id_to_context_obj(ctx: click.Context, airlock_request_id: str) -> "WorkspaceAirlockContext":
        workspace_context = ctx.find_object(WorkspaceContext)
        return WorkspaceAirlockContext(workspace_context.workspace_id, airlock_request_id)

    @property
    def airlock_id(self):
        return self.airlock_request_id


pass_workspace_airlock_context = click.make_pass_decorator(WorkspaceAirlockContext)
