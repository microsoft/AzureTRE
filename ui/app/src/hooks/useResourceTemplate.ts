import { useContext, useEffect, useRef, useState } from "react";
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
import { isRetryableApiError } from "../models/exceptions";

const TEMPLATE_TTL_MS = 5 * 60 * 1000;
const PARENT_TTL_MS = 60 * 1000;
const RETRY_BASE_MS = 5 * 1000;
const RETRY_MAX_MS = 60 * 1000;

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
  // The resource the loaded template belongs to, so a previous resource's actions are never offered for another.
  const [loadedTemplateKey, setLoadedTemplateKey] = useState<string>();
  const [loadedParentServiceId, setLoadedParentServiceId] = useState<string>();

  const resourceId = resource?.id;
  const resourceType = resource?.resourceType;
  const templateName = resource?.templateName;
  // Actions must come from the deployed template version; that is what the API validates custom actions against.
  const templateVersion = resource?.templateVersion;
  const parentServiceId = (resource as UserResource | undefined)?.parentWorkspaceServiceId;
  const workspaceId = workspaceCtx.workspace?.id;
  const workspaceScopeId = workspaceCtx.workspaceApplicationIdURI;
  const { roles, wsAuth } = getRolesForResourceType(resourceType as ResourceType);
  const userRoles = wsAuth ? workspaceCtx.roles : appRoles.roles;
  const hasRole = !!userRoles && roles.some((r) => userRoles.includes(r));

  const templateKey = `${resourceType}|${resourceId}|${templateName}|${templateVersion}|${parentServiceId}`;
  // Transient load failures are retried with backoff so actions recover without remounting.
  const [retryCount, setRetryCount] = useState(0);
  const retryState = useRef({ key: templateKey, attempts: 0 });
  if (retryState.current.key !== templateKey) retryState.current = { key: templateKey, attempts: 0 };

  useEffect(() => {
    setResourceTemplate({} as ResourceTemplate);
    setLoadedTemplateKey(undefined);
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
          setLoadedParentServiceId(parentServiceId);
          templatesPath = `${ApiEndpoint.WorkspaceServiceTemplates}/${parentService.templateName}/${ApiEndpoint.UserResourceTemplates}`;
          break;
        }
        default:
          throw Error("Unsupported resource type.");
      }

      // If the user isn't in the right role they won't see the menu at all, so skip the template.
      if (!hasRole) return;
      const templatePath = `${templatesPath}/${templateName}${
        templateVersion ? `?version=${encodeURIComponent(templateVersion)}` : ""
      }`;
      const template = await cachedGet(templatePath, TEMPLATE_TTL_MS, () => apiCall(templatePath, HttpMethod.Get));
      if (!cancelled) {
        setResourceTemplate(template);
        setLoadedTemplateKey(templateKey);
      }
    };

    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    getTemplate()
      .then(() => {
        if (!cancelled) retryState.current.attempts = 0;
      })
      .catch((e) => {
        console.warn("Failed to load resource template", e);
        // Only transient failures recover; terminal ones (e.g. 403/404) are not retried.
        if (cancelled || !isRetryableApiError(e)) return;
        const delay = Math.min(RETRY_BASE_MS * 2 ** retryState.current.attempts, RETRY_MAX_MS);
        retryState.current.attempts += 1;
        retryTimer = setTimeout(() => setRetryCount((c) => c + 1), delay);
      });
    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, [
    apiCall,
    resourceId,
    resourceType,
    templateName,
    templateVersion,
    parentServiceId,
    workspaceId,
    workspaceScopeId,
    hasRole,
    templateKey,
    retryCount,
  ]);

  const parentServiceLoaded =
    resourceType !== ResourceType.UserResource || (!!parentResource.id && loadedParentServiceId === parentServiceId);
  return {
    resourceTemplate: loadedTemplateKey === templateKey ? resourceTemplate : ({} as ResourceTemplate),
    // A workspace service's parent is the current workspace; user resources load their parent service above.
    parentResource: resourceType === ResourceType.WorkspaceService ? workspaceCtx.workspace : parentResource,
    roles: parentServiceLoaded ? roles : [],
  };
};
