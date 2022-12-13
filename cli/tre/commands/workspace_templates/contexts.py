import click


class WorkspaceTemplateContext(object):
    def __init__(self, template_name: str):
        self.template_name = template_name


pass_workspace_template_context = click.make_pass_decorator(WorkspaceTemplateContext)
