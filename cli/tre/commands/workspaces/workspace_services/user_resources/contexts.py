import click

from tre.commands.workspaces.workspace_services.contexts import WorkspaceServiceContext


class UserResourceContext(object):
    def __init__(self, workspace_id: str, workspace_service_id: str, user_resource_id):
        self.workspace_id = workspace_id
        self.workspace_service_id = workspace_service_id
        self.user_resource_id = user_resource_id

    @staticmethod
    def add_user_resource_id_to_context_obj(ctx: click.Context, user_resource_id: str) -> "UserResourceContext":
        workspace_service_context = ctx.find_object(WorkspaceServiceContext)
        return UserResourceContext(
            workspace_service_context.workspace_id,
            workspace_service_context.workspace_service_id,
            user_resource_id)


pass_user_resource_context = click.make_pass_decorator(UserResourceContext)


class UserResourceOperationContext(object):
    def __init__(self, workspace_id: str, workspace_service_id: str, user_resource_id: str, operation_id: str):
        self.workspace_id = workspace_id
        self.workspace_service_id = workspace_service_id
        self.user_resource_id = user_resource_id
        self.operation_id = operation_id

    @staticmethod
    def add_operation_id_to_context_obj(ctx: click.Context, operation_id: str) -> "UserResourceOperationContext":
        workspace_service_context = ctx.find_object(UserResourceContext)
        return UserResourceOperationContext(
            workspace_service_context.workspace_id,
            workspace_service_context.workspace_service_id,
            workspace_service_context.user_resource_id,
            operation_id)


pass_user_resource_operation_context = click.make_pass_decorator(UserResourceOperationContext)
