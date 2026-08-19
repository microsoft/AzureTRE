import copy
import semantic_version
from datetime import datetime, UTC
from typing import Optional, Tuple, List, Any

from azure.cosmos.exceptions import CosmosResourceNotFoundError
from resources.strings import RESOURCE_ACTION_INSTALL
from core import config
from db.errors import VersionDowngradeDenied, EntityDoesNotExist, MajorVersionUpdateDenied, TargetTemplateVersionDoesNotExist, UserNotAuthorizedToUseTemplate
from db.repositories.resources_history import ResourceHistoryRepository
from db.repositories.base import BaseRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from jsonschema import ValidationError, validate
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


class ResourceRepository(BaseRepository):
    @classmethod
    async def create(cls):
        cls = ResourceRepository()
        await super().create(config.STATE_STORE_RESOURCES_CONTAINER)
        return cls

    def _active_resources_by_type_query(self, resource_type: ResourceType):
        query = 'SELECT * FROM c WHERE c.deploymentStatus != @deletedStatus AND c.resourceType = @resourceType'
        parameters = [
            {'name': '@deletedStatus', 'value': Status.Deleted},
            {'name': '@resourceType', 'value': resource_type}
        ]
        return query, parameters

    def _active_resources_by_id_query(self, resource_id: str):
        query = 'SELECT * FROM c WHERE c.deploymentStatus != @deletedStatus AND c.id = @resourceId'
        parameters = [
            {'name': '@deletedStatus', 'value': Status.Deleted},
            {'name': '@resourceId', 'value': resource_id}
        ]
        return query, parameters

    @staticmethod
    def _normalize_template_schema(resource_template: dict) -> dict:
        normalized_template = copy.deepcopy(resource_template)

        def normalize_node(node, is_root=False):
            if isinstance(node, dict):
                schema_id = node.get("$id")
                if not is_root and isinstance(schema_id, str) and schema_id.partition("#")[2]:
                    node.pop("$id", None)

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
                    normalize_node(value)
            elif isinstance(node, list):
                for value in node:
                    normalize_node(value)

        normalize_node(normalized_template, is_root=True)
        return normalized_template

    @staticmethod
    def _validate_resource_parameters(resource_input, resource_template):
        normalized_template = ResourceRepository._normalize_template_schema(resource_template)
        validate(instance=resource_input["properties"], schema=normalized_template)

    async def _get_enriched_template(self, template_name: str, resource_type: ResourceType, parent_template_name: str = "") -> dict:
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
            {'name': '@templateName', 'value': template_name},
            {'name': '@deletedStatus', 'value': Status.Deleted},
            {'name': '@failedStatus', 'value': Status.DeploymentFailed}
        ]
        resources = await self.query(query=query, parameters=parameters)
        if not resources:
            raise EntityDoesNotExist
        return TypeAdapter(Resource).validate_python(resources[0])

    async def validate_input_against_template(self, template_name: str, resource_input, resource_type: ResourceType, user_roles: Optional[List[str]] = None, parent_template_name: Optional[str] = None) -> ResourceTemplate:
        try:
            template = await self._get_enriched_template(template_name, resource_type, parent_template_name)
        except EntityDoesNotExist:
            if resource_type == ResourceType.UserResource:
                raise ValueError(f'The template "{template_name}" does not exist or is not valid for the workspace service type "{parent_template_name}"')
            else:
                raise ValueError(f'The template "{template_name}" does not exist')

        # If authorizedRoles is empty, template is available to all users
        if "authorizedRoles" in template and template["authorizedRoles"]:
            # If authorizedRoles is not empty, the user is required to have at least one of authorizedRoles
            if len(set(template["authorizedRoles"]).intersection(set(user_roles))) == 0:
                raise UserNotAuthorizedToUseTemplate(f"User not authorized to use template {template_name}")

        self._validate_resource_parameters(resource_input.model_dump(), template)

        return TypeAdapter(ResourceTemplate).validate_python(template)

    def _get_all_property_keys_from_template(self, resource_template: Any, prefix: str = "") -> set:
        """
        Recursively extracts all property keys (including top-level properties, nested sub-properties
        via dotted paths like 'parent.child', and conditional properties defined in 'allOf' clauses).

        Converting templates to a set of dotted property paths ensures upgrade diff calculations
        detect newly introduced nested properties and prevent existing non-updateable conditional fields
        from being misidentified as new.
        """
        if hasattr(resource_template, "dict"):
            template_dict = resource_template.model_dump()
        elif isinstance(resource_template, dict):
            template_dict = resource_template
        else:
            template_dict = {}

        keys = set()
        properties = template_dict.get("properties", {})
        if isinstance(properties, dict):
            for k, v in properties.items():
                full_key = f"{prefix}{k}"
                keys.add(full_key)
                if isinstance(v, dict):
                    if "properties" in v:
                        keys.update(self._get_all_property_keys_from_template(v, prefix=f"{full_key}."))
                    elif "items" in v and isinstance(v["items"], dict) and "properties" in v["items"]:
                        keys.update(self._get_all_property_keys_from_template(v["items"], prefix=f"{full_key}."))

        all_of = template_dict.get("allOf")
        if all_of:
            for condition in all_of:
                if isinstance(condition, dict):
                    for clause in ["then", "else"]:
                        if clause in condition and isinstance(condition[clause], dict):
                            clause_props = condition[clause].get("properties", {})
                            if isinstance(clause_props, dict):
                                for k, v in clause_props.items():
                                    full_key = f"{prefix}{k}"
                                    keys.add(full_key)
                                    if isinstance(v, dict):
                                        if "properties" in v:
                                            keys.update(self._get_all_property_keys_from_template(v, prefix=f"{full_key}."))
                                        elif "items" in v and isinstance(v["items"], dict) and "properties" in v["items"]:
                                            keys.update(self._get_all_property_keys_from_template(v["items"], prefix=f"{full_key}."))

        system_props = template_dict.get("system_properties")
        if isinstance(system_props, dict):
            for k in system_props:
                keys.add(f"{prefix}{k}")

        return keys

    def _get_leaf_properties(self, properties: Any, prefix: str = "") -> List[Tuple[str, Any]]:
        leaves: List[Tuple[str, Any]] = []
        if isinstance(properties, dict):
            for k, v in properties.items():
                full_key = f"{prefix}{k}"
                if isinstance(v, dict) and v:
                    leaves.extend(self._get_leaf_properties(v, prefix=f"{full_key}."))
                elif isinstance(v, list) and v:
                    for index, elem in enumerate(v):
                        if isinstance(elem, dict) and elem:
                            leaves.extend(self._get_leaf_properties(elem, prefix=f"{full_key}.{index}."))
                        else:
                            leaves.append((full_key, v))
                            break
                else:
                    leaves.append((full_key, v))
        return leaves

    def _remove_property_by_path(self, target: Any, path: str):
        if not path:
            return
        parts = path.split(".")

        def remove_recursive(current: Any, parts_left: List[str]):
            if not parts_left:
                return
            key = parts_left[0]
            if len(parts_left) == 1:
                if isinstance(current, dict) and key in current:
                    del current[key]
                elif isinstance(current, list):
                    for item in current:
                        if isinstance(item, dict) and key in item:
                            del item[key]
            else:
                if isinstance(current, dict) and key in current:
                    remove_recursive(current[key], parts_left[1:])
                elif isinstance(current, list):
                    for item in current:
                        if isinstance(item, dict) and key in item:
                            remove_recursive(item[key], parts_left[1:])

        remove_recursive(target, parts)

    def _prune_empty_containers(self, obj: Any) -> bool:
        """Recursively prune empty dict/list containers. Returns True if the container is now empty."""
        if isinstance(obj, dict):
            keys_to_delete = []
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    if self._prune_empty_containers(v):
                        keys_to_delete.append(k)
            for k in keys_to_delete:
                del obj[k]
            return len(obj) == 0
        elif isinstance(obj, list):
            for item in obj:
                self._prune_empty_containers(item)
            # Remove empty dict elements from the list
            i = 0
            while i < len(obj):
                if isinstance(obj[i], dict) and len(obj[i]) == 0:
                    obj.pop(i)
                else:
                    i += 1
            return len(obj) == 0
        return False

    @staticmethod
    def _matches_if_condition(if_schema: dict, state: dict) -> bool:
        """Return whether state satisfies the JSON Schema condition."""
        if not isinstance(if_schema, dict):
            return False
        if not isinstance(state, dict):
            return False
        for key, cond in if_schema.get("properties", {}).items():
            if key not in state:
                return False
            if not isinstance(cond, dict):
                continue
            state_val = state.get(key)
            if "const" in cond:
                if state_val != cond["const"]:
                    return False
            elif "enum" in cond:
                if state_val not in cond["enum"]:
                    return False
            else:
                if state_val is None:
                    return False
        return True

    def _get_property_schema(self, schema: dict, path: str) -> Optional[dict]:
        """Resolve a dotted property path from top-level or conditional schema properties."""
        parts = path.split(".")

        def walk(properties: dict) -> Optional[dict]:
            current: Any = properties
            for index, part in enumerate(parts):
                if not isinstance(current, dict) or part not in current:
                    return None
                current = current[part]
                if index == len(parts) - 1:
                    return current if isinstance(current, dict) else None
                if not isinstance(current, dict):
                    return None
                if isinstance(current.get("items"), dict):
                    current = current["items"].get("properties", current["items"])
                else:
                    current = current.get("properties", {})
            return None

        prop = walk(schema.get("properties", {}))
        if prop:
            return prop
        for condition in schema.get("allOf", []):
            if not isinstance(condition, dict):
                continue
            for clause in ("then", "else"):
                branch = condition.get(clause)
                if isinstance(branch, dict):
                    prop = walk(branch.get("properties", {}))
                    if prop:
                        return prop
        return None

    @staticmethod
    def _get_nested_value(data: Any, path: str) -> tuple[bool, Any]:
        parts = path.split(".")

        def walk(current: Any, index: int) -> tuple[bool, Any]:
            if index == len(parts):
                return True, current
            part = parts[index]
            if isinstance(current, dict):
                if part not in current:
                    return False, None
                return walk(current[part], index + 1)
            if isinstance(current, list):
                if part.isdigit():
                    item_index = int(part)
                    if item_index >= len(current):
                        return False, None
                    return walk(current[item_index], index + 1)
                values = []
                for item in current:
                    found, value = walk(item, index)
                    if found:
                        values.append(value)
                return bool(values), values
            return False, None

        return walk(data, 0)

    @staticmethod
    def _deep_merge_dicts(base: dict, patch: dict) -> dict:
        result = copy.deepcopy(base)
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = ResourceRepository._deep_merge_dicts(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    def _deep_dict_update(self, target: dict, patch: dict):
        for k, v in patch.items():
            if isinstance(v, dict) and isinstance(target.get(k), dict):
                self._deep_dict_update(target[k], v)
            else:
                target[k] = v

    async def patch_resource(self, resource: Resource, resource_patch: ResourcePatch, resource_template: ResourceTemplate, etag: str, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository, user: User, resource_action: str, force_version_update: bool = False) -> Tuple[Resource, ResourceTemplate]:
        await resource_history_repo.create_resource_history_item(resource)
        # now update the resource props
        resource.resourceVersion = resource.resourceVersion + 1
        resource.user = user.model_dump() if hasattr(user, "model_dump") else user
        resource.updatedWhen = self.get_timestamp()

        if resource_patch.isEnabled is not None:
            resource.isEnabled = resource_patch.isEnabled

        new_template = None
        if resource_patch.templateVersion is not None:
            new_template = await self.validate_template_version_patch(resource, resource_patch, resource_template_repo, resource_template, force_version_update)

            current_template_properties = self._get_all_property_keys_from_template(resource_template)
            enriched_current_template = resource_template_repo.enrich_template(resource_template, is_update=True)
            if isinstance(enriched_current_template, dict):
                current_template_properties.update(self._get_all_property_keys_from_template(enriched_current_template))

            enriched_target_template = resource_template_repo.enrich_template(new_template, is_update=True)
            target_properties = self._get_all_property_keys_from_template(enriched_target_template)

            removed_template_paths = {path for path in current_template_properties if path not in target_properties}

            target_property_prefixes: set[str] = set()
            for target_path in target_properties:
                target_parts = target_path.split(".")
                target_property_prefixes.update(
                    ".".join(target_parts[:index]) for index in range(1, len(target_parts) + 1)
                )

            # Remove at the highest path that is completely absent from the target template,
            # for properties that were present in the current template but absent from target template.
            existing_paths = [path for path, _ in self._get_leaf_properties(resource.properties)]
            removed_top_paths: set[str] = set()
            for path in existing_paths:
                schema_path = ".".join(part for part in path.split(".") if not part.isdigit())
                schema_parts = schema_path.split(".")
                if any(
                    ".".join(schema_parts[:index]) in removed_template_paths
                    for index in range(1, len(schema_parts) + 1)
                ):
                    # Find the shortest prefix of this path that is fully absent from the target
                    remove_at = schema_path
                    for i in range(1, len(schema_parts)):
                        prefix = ".".join(schema_parts[:i])
                        # If this prefix itself is absent from target_properties and no sub-key
                        # of it exists in target_properties, remove at this level
                        if prefix not in target_property_prefixes:
                            remove_at = prefix
                            break
                    removed_top_paths.add(remove_at)

            for path in removed_top_paths:
                self._remove_property_by_path(resource.properties, path)

            # Prune empty container ancestors of removed paths that are no longer in the target schema.
            # Do NOT call _prune_empty_containers globally — that would incorrectly remove valid empty
            # arrays/dicts (e.g. rule_collections: []) that still exist in the target schema.
            for removed_path in removed_top_paths:
                parts = removed_path.split(".")
                for depth in range(len(parts) - 1, 0, -1):
                    parent_path = ".".join(parts[:depth])
                    if parent_path in target_properties:
                        break  # Ancestor is still in target schema, stop climbing
                    # Check if this ancestor container is now empty
                    curr: Any = resource.properties
                    found = True
                    for p in parent_path.split("."):
                        if not isinstance(curr, dict) or p not in curr:
                            found = False
                            break
                        curr = curr[p]
                    if found and isinstance(curr, (dict, list)) and len(curr) == 0:
                        self._remove_property_by_path(resource.properties, parent_path)

            # After schema-based removal, also strip fields that belong exclusively to inactive
            # allOf branches in the target template (evaluated against the post-patch state).
            # Without this, unevaluatedProperties:false schemas reject the upgrade payload because
            # stale fields from the old active branch are still present in resource.properties.
            post_patch_props = copy.deepcopy(resource.properties)
            if resource_patch.properties:
                post_patch_props = self._deep_merge_dicts(post_patch_props, resource_patch.properties)

            for condition in enriched_target_template.get("allOf", []):
                if not isinstance(condition, dict) or "if" not in condition:
                    continue
                matches_if = self._matches_if_condition(condition["if"], post_patch_props)
                active_branch = condition.get("then", {}) if matches_if else condition.get("else", {})
                inactive_branch = condition.get("else", {}) if matches_if else condition.get("then", {})

                inactive_props = set((inactive_branch or {}).get("properties", {}).keys())
                active_props = set((active_branch or {}).get("properties", {}).keys())
                top_level_props = set(enriched_target_template.get("properties", {}).keys())

                # Only remove props that are *exclusive* to the inactive branch
                exclusive_inactive = inactive_props - active_props - top_level_props
                for prop_key in exclusive_inactive:
                    resource.properties.pop(prop_key, None)

            resource.templateVersion = resource_patch.templateVersion

        if new_template is not None or (resource_patch.properties is not None and len(resource_patch.properties) > 0):
            await self.validate_patch(resource_patch, resource_template_repo, resource_template, resource_action, current_properties=resource.properties, target_template=new_template)

            # if we're here then we're valid - update the props + persist if present
            if resource_patch.properties is not None and len(resource_patch.properties) > 0:
                self._deep_dict_update(resource.properties, resource_patch.properties)

        await self.update_item_with_etag(resource, etag)
        return resource, new_template if new_template is not None else resource_template

    async def get_resource_dependency_list(self, resource: Resource) -> List:
        # Get the parent resource path and id
        parent_resource_path = resource.resourcePath
        dependent_resources_list = []

        # Get all related resources
        related_resources_query = "SELECT * FROM c WHERE CONTAINS(c.resourcePath, @resourcePath) AND c.deploymentStatus != @deletedStatus"
        parameters = [
            {'name': '@resourcePath', 'value': parent_resource_path},
            {'name': '@deletedStatus', 'value': Status.Deleted}
        ]
        related_resources = await self.query(query=related_resources_query, parameters=parameters)
        for resource in related_resources:
            resource_path = resource["resourcePath"]
            resource_level = resource_path.count("/")
            dependent_resources_list.append((resource, resource_level))
        # Sort resources list
        sorted_list = sorted(dependent_resources_list, key=lambda x: x[1], reverse=True)
        return [resource[0] for resource in sorted_list]

    async def validate_template_version_patch(self, resource: Resource, resource_patch: ResourcePatch, resource_template_repo: ResourceTemplateRepository, resource_template: ResourceTemplate, force_version_update: bool = False):
        parent_service_template_name = None
        if resource.resourceType == ResourceType.UserResource:
            try:
                resource_repo = await ResourceRepository.create()
                parent_service = await resource_repo.get_resource_by_id(resource.parentWorkspaceServiceId)
                parent_service_template_name = parent_service.templateName
            except EntityDoesNotExist:
                raise ValueError(f'Parent workspace service {resource.parentWorkspaceServiceId} not found')

        # validate Major upgrade
        try:
            desired_version = semantic_version.Version(resource_patch.templateVersion)
            current_version = semantic_version.Version(resource.templateVersion)
        except ValueError:
            raise ValidationError(f"Attempt to upgrade from {resource.templateVersion} to {resource_patch.templateVersion} denied. Invalid version format.")

        if not force_version_update:
            if desired_version.major > current_version.major:
                raise MajorVersionUpdateDenied(f'Attempt to upgrade from {current_version} to {desired_version} denied. major version upgrade is not allowed.')
            elif desired_version < current_version:
                raise VersionDowngradeDenied(f'Attempt to downgrade from {current_version} to {desired_version} denied. version downgrade is not allowed.')

        # validate if target template with desired version is registered
        try:
            return await resource_template_repo.get_template_by_name_and_version(resource.templateName, resource_patch.templateVersion, resource_template.resourceType, parent_service_template_name)
        except EntityDoesNotExist:
            raise TargetTemplateVersionDoesNotExist(f"Template '{resource_template.name}' not found for resource type '{resource_template.resourceType}' with target template version '{resource_patch.templateVersion}'")

    def _get_pipeline_properties(self, enriched_template, action: str = "upgrade") -> set[str]:
        properties = set()
        pipeline = enriched_template.get("pipeline")
        if pipeline and action in pipeline and pipeline[action]:
            for step in pipeline[action]:
                if step.get("stepId") != "main":
                    continue
                if "properties" in step and step["properties"]:
                    for prop in step["properties"]:
                        if isinstance(prop, dict) and prop.get("name"):
                            properties.add(prop["name"])
        return properties

    async def validate_patch(self, resource_patch: ResourcePatch, resource_template_repo: ResourceTemplateRepository, resource_template: ResourceTemplate, resource_action: str, current_properties: Optional[dict] = None, target_template: Optional[ResourceTemplate] = None):
        # get the enriched (combined) template for the old/current template
        enriched_template = resource_template_repo.enrich_template(resource_template, is_update=True)

        # get the old template properties (including allOf and system_properties) for comparison during upgrades
        old_template_properties = self._get_all_property_keys_from_template(enriched_template)

        # get the schema for the target version if upgrade is happening
        if resource_patch.templateVersion is not None:
            # fetch the template for the target version if not already provided
            if not target_template:
                parent_service_name = None
                if resource_template.resourceType == ResourceType.UserResource:
                    parent_service_name = getattr(resource_template, "parentWorkspaceService", None)

                target_template = await resource_template_repo.get_template_by_name_and_version(
                    resource_template.name,
                    resource_patch.templateVersion,
                    resource_template.resourceType,
                    parent_service_name=parent_service_name
                )
            enriched_template = resource_template_repo.enrich_template(target_template, is_update=True)

        is_upgrade = resource_patch.templateVersion is not None and resource_patch.templateVersion != resource_template.version
        action_phase = "upgrade" if is_upgrade else (resource_action if resource_action else "install")
        pipeline_properties = self._get_pipeline_properties(enriched_template, action=action_phase)

        def has_updateable_parent(path: str) -> bool:
            """
            Returns True if any ancestor object of the dotted property path is marked
            updateable: true in the template schema (including properties defined under allOf).
            """
            parts = path.split(".")
            # Walk up the chain excluding the full leaf path (checked separately)
            for i in range(len(parts) - 1, 0, -1):
                ancestor_path = ".".join(parts[:i])
                ancestor_def = self._get_property_schema(enriched_template, ancestor_path)
                if ancestor_def and ancestor_def.get("updateable", False) is True:
                    return True
            return False

        target_template_properties = self._get_all_property_keys_from_template(enriched_template)

        valid_current_properties = {}
        if current_properties:
            for k, v in current_properties.items():
                if any(prop_key == k or prop_key.startswith(f"{k}.") for prop_key in target_template_properties):
                    valid_current_properties[k] = copy.deepcopy(v)

        merged_properties = self._deep_merge_dicts(valid_current_properties, resource_patch.properties or {}) if current_properties is not None else (resource_patch.properties or {})

        def is_property_required_in_target(template_schema: dict, path: str, state: dict) -> bool:
            if not template_schema or not isinstance(template_schema, dict):
                return False

            parts = path.split(".")
            curr_schema = template_schema
            curr_state = state or {}

            for i, part in enumerate(parts):
                if not isinstance(curr_schema, dict):
                    return False

                if part.isdigit():
                    if not isinstance(curr_schema.get("items"), dict):
                        return False
                    curr_schema = curr_schema["items"]
                    if isinstance(curr_state, list) and int(part) < len(curr_state):
                        curr_state = curr_state[int(part)]
                    else:
                        curr_state = {}
                    continue

                is_part_required = False
                if "required" in curr_schema and isinstance(curr_schema["required"], list):
                    if part in curr_schema["required"]:
                        is_part_required = True

                if "allOf" in curr_schema and isinstance(curr_schema["allOf"], list):
                    for condition in curr_schema["allOf"]:
                        if isinstance(condition, dict):
                            if_cond = condition.get("if")
                            matches_if = self._matches_if_condition(if_cond, curr_state) if if_cond else False
                            branch = condition.get("then") if matches_if else condition.get("else")
                            if branch and isinstance(branch, dict) and "required" in branch and isinstance(branch["required"], list):
                                if part in branch["required"]:
                                    is_part_required = True

                if i == len(parts) - 1:
                    return is_part_required

                is_part_present = isinstance(curr_state, dict) and part in curr_state and curr_state[part] is not None
                if not is_part_required and not is_part_present:
                    return False

                next_schema = None
                if isinstance(curr_schema.get("properties"), dict) and part in curr_schema["properties"]:
                    next_schema = curr_schema["properties"][part]
                else:
                    if "allOf" in curr_schema and isinstance(curr_schema["allOf"], list):
                        for condition in curr_schema["allOf"]:
                            if isinstance(condition, dict):
                                if_cond = condition.get("if")
                                matches_if = self._matches_if_condition(if_cond, curr_state) if if_cond else False
                                branch = condition.get("then") if matches_if else condition.get("else")
                                if branch and isinstance(branch, dict) and isinstance(branch.get("properties"), dict) and part in branch["properties"]:
                                    next_schema = branch["properties"][part]
                                    break
                curr_schema = next_schema
                if isinstance(curr_state, dict):
                    curr_state = curr_state.get(part)
                elif isinstance(curr_state, list) and part.isdigit() and int(part) < len(curr_state):
                    curr_state = curr_state[int(part)]
                else:
                    curr_state = None

            return False

        def is_leaf_allowed(prop_path: str, prop_val: Any) -> bool:
            """
            Determines whether a patched leaf property path is permitted.
            Allowed if:
            1. Explicitly marked updateable: true in the template schema on the property itself
               OR on any of its ancestor objects (top-level or via allOf clauses).
            2. Introduced as a new property path during a template upgrade.
            3. Retains its existing value from the resource during an upgrade (data preservation of untouched fields).
            4. Absent from the persisted resource and required by the active target schema during an upgrade.

            Pipeline properties are retained and validated as part of the upgrade, but are not
            user-modifiable through a PATCH.
            """
            schema_path = ".".join(part for part in prop_path.split(".") if not part.isdigit())
            prop_def = self._get_property_schema(enriched_template, schema_path)
            # Allow if this leaf OR any ancestor object is marked updateable: true
            is_updateable = (prop_def.get("updateable", False) is True if prop_def else False) or has_updateable_parent(schema_path)
            is_new_on_upgrade = (
                is_upgrade
                and schema_path in target_template_properties
                and schema_path not in old_template_properties
            )

            if is_updateable or is_new_on_upgrade:
                return True

            if current_properties is not None and is_upgrade:
                has_existing, existing_val = self._get_nested_value(current_properties, prop_path)
                array_parts = prop_path.split(".")
                array_index = next((i for i, part in enumerate(array_parts) if part.isdigit()), None)
                if array_index is not None:
                    array_path = ".".join(array_parts[:array_index])
                    patch_array_exists, patch_array = self._get_nested_value(resource_patch.properties or {}, array_path)
                    current_array_exists, current_array = self._get_nested_value(current_properties, array_path)
                    if patch_array_exists and current_array_exists and (
                        not isinstance(patch_array, list)
                        or not isinstance(current_array, list)
                        or len(patch_array) != len(current_array)
                    ):
                        return False
                if has_existing and existing_val == prop_val:
                    return True

                if has_existing and prop_def and isinstance(prop_def.get("enum"), list):
                    if existing_val not in prop_def["enum"]:
                        return True

                if not has_existing and is_property_required_in_target(enriched_template, prop_path, merged_properties):
                    return True

            return False

        def is_all_leaves_allowed(prop_path: str, prop_val: Any) -> bool:
            if not isinstance(prop_val, dict):
                return is_leaf_allowed(prop_path, prop_val)
            leaves = self._get_leaf_properties({prop_path: prop_val})
            # Require every leaf in the provided property object to be allowed.
            for leaf_path, leaf_v in leaves:
                if not is_leaf_allowed(leaf_path, leaf_v):
                    return False
            # If there are no leaves (empty object), treat as not allowed to avoid accidental permits.
            return len(leaves) > 0

        # If updating/patching properties, ensure EVERY patched leaf property is allowed
        if resource_action != RESOURCE_ACTION_INSTALL and resource_patch.properties:
            leaf_props = self._get_leaf_properties(resource_patch.properties)
            for prop_path, prop_val in leaf_props:
                if not is_leaf_allowed(prop_path, prop_val):
                    schema_path = ".".join(part for part in prop_path.split(".") if not part.isdigit())
                    if schema_path in target_template_properties:
                        raise ValidationError(f"Property '{prop_path}' is not updateable.")
                    else:
                        raise ValidationError(f"Property '{prop_path}' is unexpected.")

        # validate the PATCH data against the target schema.
        update_template = copy.deepcopy(enriched_template)
        update_template["properties"] = {}

        all_template_props = {}
        if isinstance(enriched_template.get("properties"), dict):
            all_template_props.update(enriched_template["properties"])
        if isinstance(enriched_template.get("system_properties"), dict):
            all_template_props.update(enriched_template["system_properties"])

        for prop_name, prop in all_template_props.items():
            prop_val = resource_patch.properties.get(prop_name) if resource_patch.properties else None
            if (
                resource_action == RESOURCE_ACTION_INSTALL
                or prop.get("updateable", False) is True
                or (
                    is_upgrade
                    and (resource_patch.properties is not None and prop_name in resource_patch.properties)
                    and is_all_leaves_allowed(prop_name, prop_val)
                )
                or prop_name in pipeline_properties
                or (current_properties is not None and prop_name in merged_properties)
            ):
                update_template["properties"][prop_name] = copy.deepcopy(prop)

        def _adjust_required(schema_node: Any):
            if isinstance(schema_node, dict):
                if not is_upgrade and resource_action != RESOURCE_ACTION_INSTALL:
                    schema_node.pop("required", None)
                elif "required" in schema_node and isinstance(schema_node["required"], list):
                    schema_node["required"] = [r for r in schema_node["required"] if r not in pipeline_properties]
                    if not schema_node["required"]:
                        schema_node.pop("required", None)
                for v in schema_node.values():
                    _adjust_required(v)
            elif isinstance(schema_node, list):
                for item in schema_node:
                    _adjust_required(item)

        _adjust_required(update_template)

        validation_input = resource_patch.model_dump()
        validation_input["properties"] = merged_properties

        self._validate_resource_parameters(validation_input, update_template)

    def get_timestamp(self) -> float:
        return datetime.now(UTC).timestamp()
