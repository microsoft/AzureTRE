import copy
import semantic_version
from datetime import datetime, UTC
from typing import Any, Dict, Optional, Tuple, List

from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError
from resources.strings import RESOURCE_ACTION_INSTALL, REDACTED_SENSITIVE_VALUE
from core import config
from db.errors import (
    VersionDowngradeDenied,
    EntityDoesNotExist,
    MajorVersionUpdateDenied,
    TargetTemplateVersionDoesNotExist,
    UserNotAuthorizedToUseTemplate,
)
from db.repositories.resources_history import ResourceHistoryRepository
from db.repositories.base import BaseRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from jsonschema import Draft7Validator, Draft202012Validator, ValidationError, validate
from jsonschema.validators import extend, validator_for
from models.domain.authentication import User
from models.domain.resource import Resource, ResourceType
from models.domain.resource_template import ResourceTemplate
from models.domain.shared_service import SharedService
from models.domain.operation import Status
from models.domain.user_resource import UserResource
from models.domain.workspace import Workspace
from models.domain.workspace_service import WorkspaceService
from models.schemas.resource import ResourcePatch
from pydantic import UUID4, TypeAdapter
from services.logging import logger


# Keep Draft 7 keyword semantics while enforcing TRE's restriction on extra fields.
Draft7TREValidator = extend(
    Draft7Validator, {"unevaluatedProperties": Draft202012Validator.VALIDATORS["unevaluatedProperties"]}
)


def sensitive_property_names(template: dict) -> set:
    """Return the name of each property that has sensitive set to true in one or more of its declarations.

    The template can declare a name more than once, for example at the top level and in an allOf, anyOf, oneOf,
    then or else branch. A declaration without the flag does not remove it. Nested objects and array items count,
    but if conditions and the pipeline do not.
    """
    names = set()

    def collect(template_fragment: dict):
        for key, value in template_fragment.items():
            if key in ("pipeline", "if"):
                continue
            if key == "properties" and isinstance(value, dict):
                names.update(
                    name for name, prop in value.items() if isinstance(prop, dict) and prop.get("sensitive") is True
                )
            if isinstance(value, dict):
                collect(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        collect(item)

    collect(template)
    return names


def sensitive_values(properties: Dict[str, Any], template: ResourceTemplate) -> List[Tuple[tuple, Any]]:
    """Return the path and the value of each sensitive value in properties.

    A path is a tuple of keys and list indexes. A value is sensitive if its key is a sensitive property name of the
    template, also in a nested object or in an array item. The install, the update and the migration all use this
    function, so they mask the same values.
    """
    names = sensitive_property_names(template.model_dump())
    found = []

    def collect(value: Any, path: tuple):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in names:
                    found.append((path + (key,), item))
                else:
                    collect(item, path + (key,))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                collect(item, path + (index,))

    collect(properties, ())
    return found


def mask_sensitive_properties(properties: Dict[str, Any], template: ResourceTemplate) -> dict:
    masked = copy.deepcopy(properties)
    for path, _ in sensitive_values(masked, template):
        parent = masked
        for part in path[:-1]:
            parent = parent[part]
        parent[path[-1]] = REDACTED_SENSITIVE_VALUE
    return masked


def restore_sensitive_values(properties: dict, source: dict) -> dict:
    """Return a copy of properties with the real value from source in place of each placeholder.

    Two lists of the same length pair their items by index. A list with a different length keeps its placeholders,
    because its items can be different items. A null in source is a real value. Only a key that source does not have
    keeps its placeholder.
    """
    missing = object()

    def restore(value: Any, original: Any) -> Any:
        if isinstance(value, dict) and isinstance(original, dict):
            return {key: restore(item, original.get(key, missing)) for key, item in value.items()}
        if isinstance(value, list) and isinstance(original, list) and len(value) == len(original):
            return [restore(item, original_item) for item, original_item in zip(value, original)]
        if value == REDACTED_SENSITIVE_VALUE and original is not missing and original != REDACTED_SENSITIVE_VALUE:
            return copy.deepcopy(original)
        return copy.deepcopy(value)

    return restore(properties, source)


def masked_property_paths(properties: dict, template: ResourceTemplate) -> List[str]:
    """Return a JSON pointer for each sensitive value in properties that is not the placeholder."""
    return [
        "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in ("properties",) + path)
        for path, value in sensitive_values(properties, template)
        if value != REDACTED_SENSITIVE_VALUE
    ]


class ResourceRepository(BaseRepository):
    @classmethod
    async def create(cls):
        cls = ResourceRepository()
        await super().create(config.STATE_STORE_RESOURCES_CONTAINER)
        return cls

    def _active_resources_by_type_query(self, resource_type: ResourceType):
        query = "SELECT * FROM c WHERE c.deploymentStatus != @deletedStatus AND c.resourceType = @resourceType"
        parameters = [
            {"name": "@deletedStatus", "value": Status.Deleted},
            {"name": "@resourceType", "value": resource_type},
        ]
        return query, parameters

    def _active_resources_by_id_query(self, resource_id: str):
        query = "SELECT * FROM c WHERE c.deploymentStatus != @deletedStatus AND c.id = @resourceId"
        parameters = [
            {"name": "@deletedStatus", "value": Status.Deleted},
            {"name": "@resourceId", "value": resource_id},
        ]
        return query, parameters

    @staticmethod
    def _normalize_template_schema(resource_template: dict) -> dict:
        """Normalize legacy schema artifacts before validating resource input.

        jsonschema>=4.25 rejects non-empty fragment identifiers for $id.
        Historical templates include property-level values with non-empty
        fragments, such as "#/properties/foo" and "#properties/foo", which
        are not required for validation.

        Legacy templates may also contain accidental ``const: null`` constraints
        on properties that do not allow ``null`` values. Those constraints make
        the schema unsatisfiable for valid non-null input values and should be
        removed during validation normalization.
        """
        normalized_template = copy.deepcopy(resource_template)

        def _walk(node, is_root=False):
            if isinstance(node, dict):
                # Keep top-level $id intact; nested $id values with non-empty
                # fragments are invalid under newer JSON Schema metaschemas.
                schema_id = node.get("$id")
                if not is_root and isinstance(schema_id, str) and schema_id.partition("#")[2]:
                    node.pop("$id", None)

                # Remove legacy/accidental const:null if schema disallows null.
                # Keep explicit nullable const usage when type is absent or
                # nullable (e.g., type includes "null").
                if node.get("const", object()) is None:
                    schema_type = node.get("type")
                    type_allows_null = (
                        schema_type is None
                        or schema_type == "null"
                        or (isinstance(schema_type, list) and "null" in schema_type)
                    )
                    enum_values = node.get("enum")
                    enum_allows_null = not isinstance(enum_values, list) or None in enum_values

                    if not type_allows_null or not enum_allows_null:
                        node.pop("const", None)

                for value in node.values():
                    _walk(value)
            elif isinstance(node, list):
                for value in node:
                    _walk(value)

        _walk(normalized_template, is_root=True)
        return normalized_template

    @staticmethod
    def _validate_resource_parameters(resource_input, resource_template):
        normalized_template = ResourceRepository._normalize_template_schema(resource_template)
        validator_class = validator_for(normalized_template)
        if validator_class is Draft7Validator:
            validator_class = Draft7TREValidator
        validate(instance=resource_input["properties"], schema=normalized_template, cls=validator_class)

    async def _get_enriched_template(
        self, template_name: str, resource_type: ResourceType, parent_template_name: str = ""
    ) -> dict:
        template_repo = await ResourceTemplateRepository.create()
        template = await template_repo.get_current_template(template_name, resource_type, parent_template_name)
        return template_repo.enrich_template(template)

    @staticmethod
    def get_resource_base_spec_params():
        return {"tre_id": config.TRE_ID}

    async def get_resource_dict_by_id(self, resource_id: UUID4) -> dict:
        try:
            resource = await self.read_item_by_id(str(resource_id))
        except CosmosResourceNotFoundError:
            raise EntityDoesNotExist
        return resource

    async def get_resource_by_id(self, resource_id: UUID4) -> Resource:
        resource = await self.get_resource_dict_by_id(resource_id)

        if resource["resourceType"] == ResourceType.SharedService:
            return TypeAdapter(SharedService).validate_python(resource)
        if resource["resourceType"] == ResourceType.Workspace:
            return TypeAdapter(Workspace).validate_python(resource)
        if resource["resourceType"] == ResourceType.WorkspaceService:
            return TypeAdapter(WorkspaceService).validate_python(resource)
        if resource["resourceType"] == ResourceType.UserResource:
            return TypeAdapter(UserResource).validate_python(resource)
        return TypeAdapter(Resource).validate_python(resource)

    async def get_active_resource_by_template_name(self, template_name: str) -> Resource:
        query = "SELECT TOP 1 * FROM c WHERE c.templateName = @templateName AND c.deploymentStatus != @deletedStatus AND c.deploymentStatus != @failedStatus"
        parameters = [
            {"name": "@templateName", "value": template_name},
            {"name": "@deletedStatus", "value": Status.Deleted},
            {"name": "@failedStatus", "value": Status.DeploymentFailed},
        ]
        resources = await self.query(query=query, parameters=parameters)
        if not resources:
            raise EntityDoesNotExist
        return TypeAdapter(Resource).validate_python(resources[0])

    async def validate_input_against_template(
        self,
        template_name: str,
        resource_input,
        resource_type: ResourceType,
        user_roles: Optional[List[str]] = None,
        parent_template_name: Optional[str] = None,
    ) -> ResourceTemplate:
        try:
            template = await self._get_enriched_template(template_name, resource_type, parent_template_name)
        except EntityDoesNotExist:
            if resource_type == ResourceType.UserResource:
                raise ValueError(
                    f'The template "{template_name}" does not exist or is not valid for the workspace service type "{parent_template_name}"'
                )
            else:
                raise ValueError(f'The template "{template_name}" does not exist')

        # If authorizedRoles is empty, template is available to all users
        if "authorizedRoles" in template and template["authorizedRoles"]:
            # If authorizedRoles is not empty, the user is required to have at least one of authorizedRoles
            if len(set(template["authorizedRoles"]).intersection(set(user_roles))) == 0:
                raise UserNotAuthorizedToUseTemplate(f"User not authorized to use template {template_name}")

        self._validate_resource_parameters(resource_input.model_dump(), template)
        return TypeAdapter(ResourceTemplate).validate_python(template)

    async def patch_resource(
        self,
        resource: Resource,
        resource_patch: ResourcePatch,
        resource_template: ResourceTemplate,
        etag: str,
        resource_template_repo: ResourceTemplateRepository,
        resource_history_repo: ResourceHistoryRepository,
        user: User,
        resource_action: str,
        force_version_update: bool = False,
    ) -> Tuple[Resource, ResourceTemplate]:
        # A document from before the masking of updates can still have real sensitive values.
        history_resource = copy.deepcopy(resource)
        history_resource.properties = mask_sensitive_properties(resource.properties, resource_template)
        await resource_history_repo.create_resource_history_item(history_resource)
        # now update the resource props
        resource.resourceVersion = resource.resourceVersion + 1
        resource.user = user.model_dump() if hasattr(user, "model_dump") else user
        resource.updatedWhen = self.get_timestamp()

        if resource_patch.isEnabled is not None:
            resource.isEnabled = resource_patch.isEnabled

        target_template = resource_template
        if resource_patch.templateVersion is not None:
            target_template = await self.validate_template_version_patch(
                resource, resource_patch, resource_template_repo, resource_template, force_version_update
            )
            resource.templateVersion = resource_patch.templateVersion

        if resource_patch.properties is not None and len(resource_patch.properties) > 0:
            self.validate_patch(resource_patch, resource_template_repo, resource_template, resource_action)

            # if we're here then we're valid - update the props + persist
            resource.properties.update(resource_patch.properties)

        # Cosmos DB keeps sensitive values as a placeholder, as at the install. The returned resource keeps the
        # real values, because the caller builds the request message from it. The stored document has the target
        # version, so the template of that version decides which values are sensitive.
        masked_resource = copy.deepcopy(resource)
        masked_resource.properties = mask_sensitive_properties(resource.properties, target_template)
        await self.update_item_with_etag(masked_resource, etag)
        return resource, resource_template

    async def mask_stored_sensitive_values(
        self, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository
    ) -> Tuple[int, int]:
        """Replace each real sensitive value that an earlier update stored with the placeholder.

        Returns the number of resource documents and history items that changed. A second run changes nothing.
        """
        # Only resources of a template with a sensitive property, in any of its versions, can have such a value.
        names_with_sensitive_values = {
            template["name"]
            for template in await resource_template_repo.query(query="SELECT * FROM c")
            if sensitive_property_names(template)
        }
        resources = {resource["id"]: resource for resource in await self.query(query="SELECT * FROM c")}
        templates = {}

        async def template_for(resource: dict, version: str) -> Optional[ResourceTemplate]:
            resource_type = ResourceType(resource["resourceType"])
            parent_service_name = None
            if resource_type == ResourceType.UserResource:
                parent = resources.get(resource.get("parentWorkspaceServiceId"))
                if parent is None:
                    logger.warning(f"No parent workspace service for user resource {resource['id']}")
                    return None
                parent_service_name = parent["templateName"]
            key = (resource["templateName"], version, resource_type, parent_service_name)
            if key not in templates:
                try:
                    templates[key] = await resource_template_repo.get_template_by_name_and_version(*key)
                except EntityDoesNotExist:
                    logger.warning(
                        f"No template {resource['templateName']} {version} to mask resource {resource['id']}"
                    )
                    templates[key] = None
            return templates[key]

        async def mask(resource: dict, item: dict, container, partition_key: str) -> bool:
            """Replace each real sensitive value of item, which is the resource or one of its history items.

            Each patch request has the etag of the document that gave its paths. If another request changed the
            document after that read, Cosmos DB refuses the patch. Then the migration reads the document again, gets
            the template of its version and finds the paths again. After 3 refusals, the next run masks the document.
            """
            changed = False
            for _ in range(3):
                template = await template_for(resource, item.get("templateVersion") or resource["templateVersion"])
                if template is None:
                    return changed
                paths = masked_property_paths(item.get("properties") or {}, template)
                try:
                    # Cosmos DB accepts at most 10 operations in one patch request. The patched document has the etag
                    # for the next request.
                    for start in range(0, len(paths), 10):
                        item = await container.patch_item(
                            item=item["id"],
                            partition_key=partition_key,
                            patch_operations=[
                                {"op": "set", "path": path, "value": REDACTED_SENSITIVE_VALUE}
                                for path in paths[start : start + 10]
                            ],
                            etag=item["_etag"],
                            match_condition=MatchConditions.IfNotModified,
                        )
                        changed = True
                    return changed
                except CosmosAccessConditionFailedError:
                    item = await container.read_item(item=item["id"], partition_key=partition_key)
            logger.warning(
                f"Document {item['id']} changed during each attempt to mask it. The next migration masks it."
            )
            return changed

        changed_resources = 0
        changed_history_items = 0
        for resource in resources.values():
            if resource["templateName"] not in names_with_sensitive_values:
                continue
            changed_resources += await mask(resource, resource, self.container, resource["id"])

            history_items = await resource_history_repo.query(
                query="SELECT * FROM c WHERE c.resourceId = @resourceId",
                parameters=[{"name": "@resourceId", "value": resource["id"]}],
            )
            for item in history_items:
                changed_history_items += await mask(resource, item, resource_history_repo.container, item["resourceId"])

        return changed_resources, changed_history_items

    async def get_resource_dependency_list(self, resource: Resource) -> List:
        # Get the parent resource path and id
        parent_resource_path = resource.resourcePath
        dependent_resources_list = []

        # Get all related resources
        related_resources_query = (
            "SELECT * FROM c WHERE CONTAINS(c.resourcePath, @resourcePath) AND c.deploymentStatus != @deletedStatus"
        )
        parameters = [
            {"name": "@resourcePath", "value": parent_resource_path},
            {"name": "@deletedStatus", "value": Status.Deleted},
        ]
        related_resources = await self.query(query=related_resources_query, parameters=parameters)
        for resource in related_resources:
            resource_path = resource["resourcePath"]
            resource_level = resource_path.count("/")
            dependent_resources_list.append((resource, resource_level))
        # Sort resources list
        sorted_list = sorted(dependent_resources_list, key=lambda x: x[1], reverse=True)
        return [resource[0] for resource in sorted_list]

    async def validate_template_version_patch(
        self,
        resource: Resource,
        resource_patch: ResourcePatch,
        resource_template_repo: ResourceTemplateRepository,
        resource_template: ResourceTemplate,
        force_version_update: bool = False,
    ) -> ResourceTemplate:
        """Return the template of the target version."""
        parent_service_template_name = None
        if resource.resourceType == ResourceType.UserResource:
            try:
                resource_repo = await ResourceRepository.create()
                parent_service = await resource_repo.get_resource_by_id(resource.parentWorkspaceServiceId)
                parent_service_template_name = parent_service.templateName
            except EntityDoesNotExist:
                raise ValueError(f"Parent workspace service {resource.parentWorkspaceServiceId} not found")

        # validate Major upgrade
        try:
            desired_version = semantic_version.Version(resource_patch.templateVersion)
            current_version = semantic_version.Version(resource.templateVersion)
        except ValueError:
            raise ValidationError(
                f"Attempt to upgrade from {resource.templateVersion} to {resource_patch.templateVersion} denied. Invalid version format."
            )

        if not force_version_update:
            if desired_version.major > current_version.major:
                raise MajorVersionUpdateDenied(
                    f"Attempt to upgrade from {current_version} to {desired_version} denied. major version upgrade is not allowed."
                )
            elif desired_version < current_version:
                raise VersionDowngradeDenied(
                    f"Attempt to downgrade from {current_version} to {desired_version} denied. version downgrade is not allowed."
                )

        # validate if target template with desired version is registered
        try:
            return await resource_template_repo.get_template_by_name_and_version(
                resource.templateName,
                resource_patch.templateVersion,
                resource_template.resourceType,
                parent_service_template_name,
            )
        except EntityDoesNotExist:
            raise TargetTemplateVersionDoesNotExist(
                f"Template '{resource_template.name}' not found for resource type '{resource_template.resourceType}' with target template version '{resource_patch.templateVersion}'"
            )

    def validate_patch(
        self,
        resource_patch: ResourcePatch,
        resource_template_repo: ResourceTemplateRepository,
        resource_template: ResourceTemplate,
        resource_action: str,
    ):
        # get the enriched (combined) template
        enriched_template = resource_template_repo.enrich_template(resource_template, is_update=True)

        # validate the PATCH data against a cut down version of the full template.
        update_template = copy.deepcopy(enriched_template)
        update_template["required"] = []
        update_template["properties"] = {}
        for prop_name, prop in enriched_template["properties"].items():
            if resource_action == RESOURCE_ACTION_INSTALL or prop.get("updateable", False) is True:
                update_template["properties"][prop_name] = prop

        self._validate_resource_parameters(resource_patch.model_dump(), update_template)

    def get_timestamp(self) -> float:
        return datetime.now(UTC).timestamp()
