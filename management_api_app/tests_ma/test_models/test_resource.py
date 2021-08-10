import pytest

from models.domain.resource import Resource, ResourceType


@pytest.mark.parametrize('resource, expected', [
    # enabled = True
    (Resource(resourceTemplateName="", resourceTemplateVersion="", resourceTemplateParameters={"enabled": True}, id="1234", resourceType=ResourceType.Workspace), True),
    # enabled = False
    (Resource(resourceTemplateName="", resourceTemplateVersion="", resourceTemplateParameters={"enabled": False}, id="1234", resourceType=ResourceType.Workspace), False),
    # enabled not set - defaults to True
    (Resource(resourceTemplateName="", resourceTemplateVersion="", resourceTemplateParameters={}, id="1234", resourceType=ResourceType.Workspace), True),
])
def test_resource_is_enabled_returns_correct_value(resource, expected):
    assert resource.is_enabled() == expected
