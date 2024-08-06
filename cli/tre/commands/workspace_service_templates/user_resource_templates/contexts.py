import click


from tre.commands.workspace_service_templates.contexts import WorkspaceServiceTemplateContext


class UserResourceTemplateContext(object):
    def __init__(self, workspace_service_name: str, template_name: str):
        self.workspace_service_name = workspace_service_name
        self.template_name = template_name

    @staticmethod
    def add_template_name_to_context_obj(ctx: click.Context, template_name: str) -> "UserResourceTemplateContext":
        workspace_service_template_context = ctx.find_object(WorkspaceServiceTemplateContext)
        return UserResourceTemplateContext(workspace_service_template_context.template_name, template_name)


pass_user_resource_template_context = click.make_pass_decorator(UserResourceTemplateContext)
