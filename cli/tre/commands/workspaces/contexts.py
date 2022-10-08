import click


class WorkspaceContext(object):
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id


pass_workspace_context = click.make_pass_decorator(WorkspaceContext)


class WorkspaceOperationContext(object):
    def __init__(self, workspace_id: str, operation_id: str):
        self.workspace_id = workspace_id
        self.operation_id = operation_id

    @staticmethod
    def add_operation_id_to_context_obj(ctx: click.Context, operation_id: str) -> "WorkspaceOperationContext":
        workspace_context = ctx.find_object(WorkspaceContext)
        return WorkspaceOperationContext(workspace_context.workspace_id, operation_id)


pass_workspace_operation_context = click.make_pass_decorator(WorkspaceOperationContext)
