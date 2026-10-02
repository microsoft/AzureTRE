import { useContext, useEffect, useState } from "react";
import { WorkspaceContext } from "../contexts/WorkspaceContext";
import { AppRolesContext } from "../contexts/AppRolesContext";
import { ApiEndpoint } from "../models/apiEndpoints";
import { Resource } from "../models/resource";
import { ResourceTemplate } from "../models/resourceTemplate";
import { ResourceType } from "../models/resourceType";
import { RoleName, WorkspaceRoleName } from "../models/roleNames";
import { UserResource } from "../models/userResource";
import { Workspace } from "../models/workspace";
import { WorkspaceService } from "../models/workspaceService";
import { HttpMethod, useAuthApiCall } from "./useAuthApiCall";

const TEMPLATE_TTL_MS = 5 * 60 * 1000;
const PARENT_TTL_MS = 60 * 1000;

// Shared across cards so a list of N resources from the same template doesn't make N identical requests.
const requestCache = new Map<string, { expires: number; promise: Promise<any> }>();

export const clearResourceTemplateCache = () => requestCache.clear();

const cachedGet = (key: string, ttl: number, fetcher: () => Promise<any>) => {
  const cached = requestCache.get(key);
  if (cached && cached.expires > Date.now()) return cached.promise;
  const promise = fetcher().catch((e) => {
    requestCache.delete(key);
    throw e;
  });
  requestCache.set(key, { expires: Date.now() + ttl, promise });
  return promise;
};

export const getRolesForResourceType = (resourceType: ResourceType) => {
  switch (resourceType) {
    case ResourceType.SharedService:
      return { roles: [RoleName.TREAdmin, WorkspaceRoleName.WorkspaceOwner] as Array<string>, wsAuth: false };
    case ResourceType.WorkspaceService:
      return { roles: [WorkspaceRoleName.WorkspaceOwner] as Array<string>, wsAuth: true };
    case ResourceType.UserResource:
      return {
        roles: [
          WorkspaceRoleName.WorkspaceOwner,
          WorkspaceRoleName.WorkspaceResearcher,
          WorkspaceRoleName.AirlockManager,
        ] as Array<string>,
        wsAuth: true,
      };
    case ResourceType.Workspace:
      return { roles: [RoleName.TREAdmin] as Array<string>, wsAuth: false };
    default:
      return { roles: [] as Array<string>, wsAuth: false };
  }
};

export const useResourceTemplate = (resource: Resource | undefined) => {
  const apiCall = useAuthApiCall();
  const workspaceCtx = useContext(WorkspaceContext);
  const appRoles = useContext(AppRolesContext);
  const [resourceTemplate, setResourceTemplate] = useState({} as ResourceTemplate);
  const [parentResource, setParentResource] = useState({} as WorkspaceService | Workspace);

  const resourceId = resource?.id;
  const resourceType = resource?.resourceType;
  const templateName = resource?.templateName;
  const parentServiceId = (resource as UserResource | undefined)?.parentWorkspaceServiceId;
  const workspaceId = workspaceCtx.workspace?.id;
  const workspaceScopeId = workspaceCtx.workspaceApplicationIdURI;
  const { roles, wsAuth } = getRolesForResourceType(resourceType as ResourceType);
  const userRoles = wsAuth ? workspaceCtx.roles : appRoles.roles;
  const hasRole = !!userRoles && roles.some((r) => userRoles.includes(r));

  useEffect(() => {
    if (!resourceId || !resourceType || !templateName) return;
    let cancelled = false;

    const getTemplate = async () => {
      let templatesPath;
      switch (resourceType) {
        case ResourceType.Workspace:
          templatesPath = ApiEndpoint.WorkspaceTemplates;
          break;
        case ResourceType.WorkspaceService:
          templatesPath = ApiEndpoint.WorkspaceServiceTemplates;
          break;
        case ResourceType.SharedService:
          templatesPath = ApiEndpoint.SharedServiceTemplates;
          break;
        case ResourceType.UserResource: {
          const parentPath = `${ApiEndpoint.Workspaces}/${workspaceId}/${ApiEndpoint.WorkspaceServices}/${parentServiceId}`;
          const parentService = (
            await cachedGet(`${parentPath}|${workspaceScopeId}`, PARENT_TTL_MS, () =>
              apiCall(parentPath, HttpMethod.Get, workspaceScopeId),
            )
          ).workspaceService as WorkspaceService;
          if (cancelled) return;
          setParentResource(parentService);
          templatesPath = `${ApiEndpoint.WorkspaceServiceTemplates}/${parentService.templateName}/${ApiEndpoint.UserResourceTemplates}`;
          break;
        }
        default:
          throw Error("Unsupported resource type.");
      }

      // If the user isn't in the right role they won't see the menu at all, so skip the template.
      if (!hasRole) return;
      const templatePath = `${templatesPath}/${templateName}`;
      const template = await cachedGet(templatePath, TEMPLATE_TTL_MS, () => apiCall(templatePath, HttpMethod.Get));
      if (!cancelled) setResourceTemplate(template);
    };

    getTemplate().catch((e) => console.warn("Failed to load resource template", e));
    return () => {
      cancelled = true;
    };
  }, [apiCall, resourceId, resourceType, templateName, parentServiceId, workspaceId, workspaceScopeId, hasRole]);

  return { resourceTemplate, parentResource, roles };
};
