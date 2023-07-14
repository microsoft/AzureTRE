import click

from tre.commands.workspaces.contexts import WorkspaceContext


class WorkspaceServiceContext(object):
    def __init__(self, workspace_id: str, workspace_service_id: str):
        self.workspace_id = workspace_id
        self.workspace_service_id = workspace_service_id

    @staticmethod
    def add_service_id_to_context_obj(ctx: click.Context, workspace_service_id: str) -> "WorkspaceServiceContext":
        workspace_context = ctx.find_object(WorkspaceContext)
        return WorkspaceServiceContext(workspace_context.workspace_id, workspace_service_id)


pass_workspace_service_context = click.make_pass_decorator(WorkspaceServiceContext)


class WorkspaceServiceOperationContext(object):
    def __init__(self, workspace_id: str, workspace_service_id: str, operation_id: str):
        self.workspace_id = workspace_id
        self.workspace_service_id = workspace_service_id
        self.operation_id = operation_id

    @staticmethod
    def add_operation_id_to_context_obj(ctx: click.Context, operation_id: str) -> "WorkspaceServiceOperationContext":
        workspace_service_context = ctx.find_object(WorkspaceServiceContext)
        return WorkspaceServiceOperationContext(workspace_service_context.workspace_id, workspace_service_context.workspace_service_id, operation_id)


pass_workspace_service_operation_context = click.make_pass_decorator(WorkspaceServiceOperationContext)
