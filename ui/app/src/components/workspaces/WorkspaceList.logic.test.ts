// Simple unit tests for the WorkspaceList sorting and filtering logic
// These test the core business logic without complex UI testing

import { describe, it, expect } from "vitest";
import { Workspace } from "../../models/workspace";
import { ResourceType } from "../../models/resourceType";

// Mock workspace data for testing
const createMockWorkspace = (
  id: string,
  displayName: string,
  updatedWhen: number,
): Workspace => ({
  id,
  isEnabled: true,
  resourcePath: `/workspaces/${id}`,
  resourceVersion: 1,
  resourceType: ResourceType.Workspace,
  templateName: "base-workspace",
  templateVersion: "1.0.0",
  availableUpgrades: [],
  deploymentStatus: "deployed",
  updatedWhen,
  user: { id: "user1", email: "user1@test.com" },
  history: [],
  _etag: "etag1",
  properties: {
    display_name: displayName,
  },
  workspaceURL: `https://${id}.example.com`,
});

const mockWorkspaces: Workspace[] = [
  createMockWorkspace("workspace-beta", "Beta Workspace", 1609459200), // 2021-01-01
  createMockWorkspace("workspace-alpha", "Alpha Workspace", 1609545600), // 2021-01-02
  createMockWorkspace("workspace-gamma", "Gamma Workspace", 1609632000), // 2021-01-03
];

// Sorting functions extracted from WorkspaceList logic
const sortWorkspacesByName = (workspaces: Workspace[], ascending = true) => {
  return [...workspaces].sort((a, b) => {
    const nameA = a.properties?.display_name || a.id;
    const nameB = b.properties?.display_name || b.id;
    const comparison = nameA.localeCompare(nameB);
    return ascending ? comparison : -comparison;
  });
};

const sortWorkspacesById = (workspaces: Workspace[], ascending = true) => {
  return [...workspaces].sort((a, b) => {
    const comparison = a.id.localeCompare(b.id);
    return ascending ? comparison : -comparison;
  });
};

const sortWorkspacesByCreated = (workspaces: Workspace[], ascending = true) => {
  return [...workspaces].sort((a, b) => {
    const comparison = a.updatedWhen - b.updatedWhen;
    return ascending ? comparison : -comparison;
  });
};

// Filtering function extracted from WorkspaceList logic
const filterWorkspaces = (workspaces: Workspace[], searchTerm: string) => {
  if (!searchTerm.trim()) {
    return workspaces;
  }

  const searchLower = searchTerm.toLowerCase();
  return workspaces.filter((workspace) => {
    const displayName = workspace.properties?.display_name?.toLowerCase() || "";
    const workspaceId = workspace.id.toLowerCase();
    return displayName.includes(searchLower) || workspaceId.includes(searchLower);
  });
};

describe("WorkspaceList Business Logic", () => {
  describe("Sorting", () => {
    it("sorts by name ascending correctly", () => {
      const sorted = sortWorkspacesByName(mockWorkspaces, true);
      expect(sorted[0].properties.display_name).toBe("Alpha Workspace");
      expect(sorted[1].properties.display_name).toBe("Beta Workspace");
      expect(sorted[2].properties.display_name).toBe("Gamma Workspace");
    });

    it("sorts by name descending correctly", () => {
      const sorted = sortWorkspacesByName(mockWorkspaces, false);
      expect(sorted[0].properties.display_name).toBe("Gamma Workspace");
      expect(sorted[1].properties.display_name).toBe("Beta Workspace");
      expect(sorted[2].properties.display_name).toBe("Alpha Workspace");
    });

    it("sorts by ID ascending correctly", () => {
      const sorted = sortWorkspacesById(mockWorkspaces, true);
      expect(sorted[0].id).toBe("workspace-alpha");
      expect(sorted[1].id).toBe("workspace-beta");
      expect(sorted[2].id).toBe("workspace-gamma");
    });

    it("sorts by ID descending correctly", () => {
      const sorted = sortWorkspacesById(mockWorkspaces, false);
      expect(sorted[0].id).toBe("workspace-gamma");
      expect(sorted[1].id).toBe("workspace-beta");
      expect(sorted[2].id).toBe("workspace-alpha");
    });

    it("sorts by creation date ascending correctly", () => {
      const sorted = sortWorkspacesByCreated(mockWorkspaces, true);
      expect(sorted[0].updatedWhen).toBe(1609459200); // earliest
      expect(sorted[1].updatedWhen).toBe(1609545600);
      expect(sorted[2].updatedWhen).toBe(1609632000); // latest
    });

    it("sorts by creation date descending correctly", () => {
      const sorted = sortWorkspacesByCreated(mockWorkspaces, false);
      expect(sorted[0].updatedWhen).toBe(1609632000); // latest
      expect(sorted[1].updatedWhen).toBe(1609545600);
      expect(sorted[2].updatedWhen).toBe(1609459200); // earliest
    });
  });

  describe("Filtering", () => {
    it("filters by workspace name (case insensitive)", () => {
      const filtered = filterWorkspaces(mockWorkspaces, "alpha");
      expect(filtered).toHaveLength(1);
      expect(filtered[0].properties.display_name).toBe("Alpha Workspace");
    });

    it("filters by workspace name with uppercase", () => {
      const filtered = filterWorkspaces(mockWorkspaces, "BETA");
      expect(filtered).toHaveLength(1);
      expect(filtered[0].properties.display_name).toBe("Beta Workspace");
    });

    it("filters by workspace ID", () => {
      const filtered = filterWorkspaces(mockWorkspaces, "workspace-gamma");
      expect(filtered).toHaveLength(1);
      expect(filtered[0].id).toBe("workspace-gamma");
    });

    it("filters by partial workspace ID", () => {
      const filtered = filterWorkspaces(mockWorkspaces, "gamma");
      expect(filtered).toHaveLength(1);
      expect(filtered[0].id).toBe("workspace-gamma");
    });

    it("filters by partial name match", () => {
      const filtered = filterWorkspaces(mockWorkspaces, "Workspace");
      expect(filtered).toHaveLength(3); // All contain "Workspace"
    });

    it("returns empty array for no matches", () => {
      const filtered = filterWorkspaces(mockWorkspaces, "nonexistent");
      expect(filtered).toHaveLength(0);
    });

    it("returns all workspaces for empty search term", () => {
      const filtered = filterWorkspaces(mockWorkspaces, "");
      expect(filtered).toHaveLength(3);
      expect(filtered).toEqual(mockWorkspaces);
    });

    it("returns all workspaces for whitespace-only search term", () => {
      const filtered = filterWorkspaces(mockWorkspaces, "   ");
      expect(filtered).toHaveLength(3);
      expect(filtered).toEqual(mockWorkspaces);
    });
  });

  describe("Combined Sorting and Filtering", () => {
    it("filters then sorts correctly", () => {
      const workspacesWithWorkspace = filterWorkspaces(mockWorkspaces, "Workspace");
      const sortedFiltered = sortWorkspacesByName(workspacesWithWorkspace, true);
      
      expect(sortedFiltered).toHaveLength(3);
      expect(sortedFiltered[0].properties.display_name).toBe("Alpha Workspace");
      expect(sortedFiltered[1].properties.display_name).toBe("Beta Workspace");
      expect(sortedFiltered[2].properties.display_name).toBe("Gamma Workspace");
    });
  });
});