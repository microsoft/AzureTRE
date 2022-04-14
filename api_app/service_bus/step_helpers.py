from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.authentication import User
from models.domain.resource_template import PipelineStep, ResourceTemplate
from models.schemas.resource import ResourcePatch
from db.repositories.resources import ResourceRepository


def update_resource_for_step(template_step: PipelineStep, resource_repo: ResourceRepository, resource_template_repo: ResourceTemplateRepository, resource_template: ResourceTemplate, user: User):
    # - get the resource to send from cosmos
    # - update the props
    # - save the resource
    # - send the action to SB

    # create properties dict - for now we create a basic, string only dict to use as a patch
    properties = {}
    for prop in template_step.properties:
        # TODO: actual substitution logic #1679
        properties[prop.name] = prop.value

    if template_step.resourceAction == "upgrade":
        # get the resource to upgrade - currently just the top 1 by template name. more complexity around querying tbd.
        resource = resource_repo.get_resource_by_template_name(template_step.resourceTemplateName)

        # create the patch
        patch = ResourcePatch(
            properties=properties
        )

        # validate and submit the patch
        resource_to_send = resource_repo.patch_resource(
            resource=resource,
            resource_patch=patch,
            resource_template=resource_template,
            etag=resource.etag,
            resource_template_repo=resource_template_repo,
            user=user)

        return resource_to_send

    else:
        raise Exception("Only upgrade is currently supported for pipeline steps")
