import copy
import re
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


def local_definition(root: dict, ref: str) -> Any:
    """Return the part of root that a local reference such as #/$defs/label points to, or None."""
    if not ref.startswith("#/"):
        return None
    part = root
    for key in ref[2:].split("/"):
        key = key.replace("~1", "/").replace("~0", "~")
        if not isinstance(part, dict) or key not in part:
            return None
        part = part[key]
    return part


def declares_sensitive(schema: Any, root: dict, refs: set) -> bool:
    """Return True if schema, a part of it or a definition that it references has sensitive set to true."""
    if isinstance(schema, list):
        return any(declares_sensitive(item, root, refs) for item in schema)
    if not isinstance(schema, dict):
        return False
    if schema.get("sensitive") is True:
        return True
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref not in refs:
        refs.add(ref)
        if declares_sensitive(local_definition(root, ref), root, refs):
            return True
    return any(declares_sensitive(value, root, refs) for key, value in schema.items() if key != "if")


def sensitive_schema(schema: Any, root: Optional[dict] = None, refs: tuple = ()) -> dict:
    """Return the schema paths to the sensitive properties of a template, or of a part of a template.

    Each node is a dict with only the keys that lead to a sensitive value, so an empty dict means that the schema has
    no sensitive property:
    - "sensitive": True for a sensitive value.
    - "properties": the node of each key that properties names.
    - "patternProperties": the node of the keys that match each pattern.
    - "additionalProperties": a list of nodes for the other keys. Each node has the names and the patterns of its own
      schema, because additionalProperties applies only to the keys that its own schema does not name.
      unevaluatedProperties uses the same rule, so it can mask a key that a branch evaluates.
    - "prefixItems": the node of each list item by its index.
    - "items": the node of all list items. A sensitive flag under contains applies to each item. If the same schema
      has prefixItems, the node of items or unevaluatedItems goes in "itemsAfter".
    - "itemsAfter": a list of nodes for the items after the prefixItems of their own schema, each with its start.

    The allOf, anyOf, oneOf, then, else, dependentSchemas and dependencies keywords and a local $ref at one place in
    the schema describe the same place in the data. So the nodes of all declarations at that place merge, and a
    declaration without the flag does not remove it. The if conditions and the pipeline do not count. Root is the
    template that a $ref points into, and refs are the references on the current path.
    """
    node = {}
    if not isinstance(schema, dict):
        return node
    root = schema if root is None else root
    if schema.get("sensitive") is True:
        node["sensitive"] = True
    for keyword in ("properties", "patternProperties"):
        for name, declaration in (schema.get(keyword) or {}).items():
            child = sensitive_schema(declaration, root, refs)
            if child:
                merge_sensitive_schema(node.setdefault(keyword, {}).setdefault(name, {}), child)
    names = list(schema.get("properties") or {})
    patterns = list(schema.get("patternProperties") or {})
    for keyword in ("additionalProperties", "unevaluatedProperties"):
        other_keys = sensitive_schema(schema.get(keyword), root, refs)
        if other_keys:
            node.setdefault("additionalProperties", []).append(
                {"names": names, "patterns": patterns, "node": other_keys}
            )
    prefix = schema.get("prefixItems") or []
    for index, declaration in enumerate(prefix):
        child = sensitive_schema(declaration, root, refs)
        if child:
            prefix_nodes = node.setdefault("prefixItems", [])
            prefix_nodes.extend({} for _ in range(index + 1 - len(prefix_nodes)))
            merge_sensitive_schema(prefix_nodes[index], child)
    for keyword in ("items", "unevaluatedItems"):
        items = sensitive_schema(schema.get(keyword), root, refs)
        if items and prefix:
            node.setdefault("itemsAfter", []).append({"start": len(prefix), "node": items})
        elif items:
            merge_sensitive_schema(node.setdefault("items", {}), items)
    contains = sensitive_schema(schema.get("contains"), root, refs)
    if contains:
        merge_sensitive_schema(node.setdefault("items", {}), contains)
    branches = [schema.get("then"), schema.get("else")]
    for keyword in ("allOf", "anyOf", "oneOf"):
        branches.extend(schema.get(keyword) or [])
    for keyword in ("dependentSchemas", "dependencies"):
        branches.extend((schema.get(keyword) or {}).values())
    for branch in branches:
        merge_sensitive_schema(node, sensitive_schema(branch, root, refs))
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref not in refs:
        merge_sensitive_schema(node, sensitive_schema(local_definition(root, ref), root, refs + (ref,)))
    elif isinstance(ref, str) and declares_sensitive(local_definition(root, ref), root, {ref}):
        # A recursive reference has no last path. If its definition has a sensitive value, the whole value is sensitive.
        node["sensitive"] = True
    return node


def merge_sensitive_schema(target: dict, source: dict):
    if source.get("sensitive"):
        target["sensitive"] = True
    for keyword in ("properties", "patternProperties"):
        for name, child in source.get(keyword, {}).items():
            merge_sensitive_schema(target.setdefault(keyword, {}).setdefault(name, {}), child)
    target_prefix = target.setdefault("prefixItems", []) if "prefixItems" in source else None
    for index, child in enumerate(source.get("prefixItems", [])):
        target_prefix.extend({} for _ in range(index + 1 - len(target_prefix)))
        merge_sensitive_schema(target_prefix[index], child)
    if "items" in source:
        merge_sensitive_schema(target.setdefault("items", {}), source["items"])
    for keyword in ("additionalProperties", "itemsAfter"):
        if keyword in source:
            target.setdefault(keyword, []).extend(source[keyword])


def matches(pattern: str, key: str) -> bool:
    """Return True if key matches the pattern, as the jsonschema validator matches it. A pattern that Python cannot
    read matches each key, so that no sensitive value stays unmasked."""
    try:
        return re.search(pattern, key) is not None
    except re.error:
        return True


def node_for_key(node: dict, key: str) -> dict:
    """Return the merged node of the declarations that apply to one key of an object."""
    child = {}
    if key in node.get("properties", {}):
        merge_sensitive_schema(child, node["properties"][key])
    for pattern, pattern_node in node.get("patternProperties", {}).items():
        if matches(pattern, key):
            merge_sensitive_schema(child, pattern_node)
    for additional in node.get("additionalProperties", []):
        if key not in additional["names"] and not any(matches(pattern, key) for pattern in additional["patterns"]):
            merge_sensitive_schema(child, additional["node"])
    return child


def node_for_index(node: dict, index: int) -> dict:
    """Return the merged node of the declarations that apply to one list item."""
    child = {}
    prefix = node.get("prefixItems", [])
    if index < len(prefix):
        merge_sensitive_schema(child, prefix[index])
    merge_sensitive_schema(child, node.get("items", {}))
    for after in node.get("itemsAfter", []):
        if index >= after["start"]:
            merge_sensitive_schema(child, after["node"])
    return child


def sensitive_values(properties: Dict[str, Any], template: ResourceTemplate) -> List[Tuple[tuple, Any]]:
    """Return the path and the value of each sensitive value in properties.

    A path is a tuple of keys and list indexes. A value is sensitive if the template declares it as sensitive at the
    same schema path, also in a nested object or in an array item. A key with the same name at a different path is
    not sensitive. The install, the update and the migration all use this function, so they mask the same values.
    """
    found = []

    def collect(value: Any, node: dict, path: tuple):
        if node.get("sensitive"):
            found.append((path, value))
        elif isinstance(value, dict):
            for key, item in value.items():
                child = node_for_key(node, key)
                if child:
                    collect(item, child, path + (key,))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                child = node_for_index(node, index)
                if child:
                    collect(item, child, path + (index,))

    node = sensitive_schema(template.model_dump())
    if node.get("sensitive"):
        # A branch at the top level can have the flag. The properties must stay an object, so each property is masked.
        node = {"properties": {key: {"sensitive": True} for key in properties}}
    collect(properties, node, ())
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
            if sensitive_schema(template)
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
