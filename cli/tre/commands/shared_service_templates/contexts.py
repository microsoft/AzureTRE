import click


class SharedServiceTemplateContext(object):
    def __init__(self, template_name: str):
        self.template_name = template_name


pass_shared_service_template_context = click.make_pass_decorator(SharedServiceTemplateContext)
