import click


class WorkspaceServiceTemplateContext(object):
    def __init__(self, template_name: str):
        self.template_name = template_name


pass_workspace_service_template_context = click.make_pass_decorator(WorkspaceServiceTemplateContext)
