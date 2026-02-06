import { Resource } from '../models/resource';
import { Workspace } from '../models/workspace';
import { WorkspaceService } from '../models/workspaceService';
import { ResourceType } from '../models/resourceType';
import { Operation } from '../models/operation';
import { CostResource } from '../models/costs';

export const mockWorkspace: Workspace = {
  id: 'test-workspace-id',
  resourcePath: '/workspaces/test-workspace-id',
  resourceVersion: 1,
  resourceType: ResourceType.Workspace,
  templateName: 'base-workspace',
  templateVersion: '1.0.0',
  availableUpgrades: [],
  deploymentStatus: 'deployed',
  updatedWhen: Date.now(),
  isEnabled: true,
  user: {
    name: 'Test User',
    id: 'test-user-id',
    email: 'test@example.com',
    roleAssignments: [],
    roles: []
  },
  history: [],
  _etag: 'test-etag',
  properties: {
    scope_id: 'test-scope-id',
    workspace_name: 'Test Workspace',
    description: 'A test workspace',
  },
  workspaceURL: 'https://test-workspace.example.com',
};

export const mockWorkspaceService: WorkspaceService = {
  id: 'test-service-id',
  resourcePath: '/workspaces/test-workspace-id/workspace-services/test-service-id',
  resourceVersion: 1,
  resourceType: ResourceType.WorkspaceService,
  templateName: 'test-service',
  templateVersion: '1.0.0',
  availableUpgrades: [],
  deploymentStatus: 'deployed',
  updatedWhen: Date.now(),
  isEnabled: true,
  user: {
    name: 'Test User',
    id: 'test-user-id',
    email: 'test@example.com',
    roleAssignments: [],
    roles: []
  },
  history: [],
  _etag: 'test-etag',
  properties: {
    display_name: 'Test Service',
    description: 'A test workspace service',
  },
  workspaceId: 'test-workspace-id',
};

export const mockUserResource: Resource = {
  id: 'test-user-resource-id',
  resourcePath: '/workspaces/test-workspace-id/workspace-services/test-service-id/user-resources/test-user-resource-id',
  resourceVersion: 1,
  resourceType: ResourceType.UserResource,
  templateName: 'test-user-resource',
  templateVersion: '1.0.0',
  availableUpgrades: [],
  deploymentStatus: 'deployed',
  updatedWhen: Date.now(),
  isEnabled: true,
  user: {
    name: 'Test User',
    id: 'test-user-id',
    email: 'test@example.com',
    roleAssignments: [],
    roles: []
  },
  history: [],
  _etag: 'test-etag',
  properties: {
    display_name: 'Test User Resource',
    description: 'A test user resource',
  },
};

export const mockOperation: Operation = {
  id: 'test-operation-id',
  resourceId: 'test-workspace-id',
  resourcePath: '/workspaces/test-workspace-id',
  resourceVersion: 1,
  status: 'deployed',
  action: 'install',
  message: 'Successfully deployed',
  createdWhen: Date.now(),
  updatedWhen: Date.now(),
  user: {
    name: 'Test User',
    id: 'test-user-id',
    email: 'test@example.com',
    roleAssignments: [],
    roles: []
  },
  steps: [],
};

export const mockCostResource: CostResource = {
  id: 'test-cost-id',
  name: 'Test Workspace',
  costs: [
    {
      cost: 100.50,
      currency: 'USD',
      date: '2024-01-01',
    }
  ]
};
