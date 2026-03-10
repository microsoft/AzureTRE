import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, createPartialFluentUIMock } from "../../test-utils";
import { StatusBadge } from "./StatusBadge";
import { Resource } from "../../models/resource";
import { ResourceType } from "../../models/resourceType";

// Mock FluentUI components using centralized mocks
vi.mock("@fluentui/react", async () => {
  const actual = await vi.importActual("@fluentui/react");
  return {
    ...actual,
    ...createPartialFluentUIMock([
      'Stack',
      'Text',
      'Spinner',
      'FontIcon',
      'TooltipHost',
    ]),
  };
});

const mockResource: Resource = {
  id: "test-resource-id",
  resourceType: ResourceType.Workspace,
  templateName: "test-template",
  templateVersion: "1.0.0",
  resourcePath: "/workspaces/test-resource-id",
  resourceVersion: 1,
  isEnabled: true,
  properties: {
    display_name: "Test Resource",
  },
  _etag: "test-etag",
  updatedWhen: Date.now(),
  deploymentStatus: "deployed",
  availableUpgrades: [],
  history: [],
  user: {
    id: "test-user-id",
    name: "Test User",
    email: "test@example.com",
    roleAssignments: [],
    roles: ["workspace_researcher"],
  },
};

describe("StatusBadge Component", () => {
  it("renders spinner for in-progress status", () => {
    render(<StatusBadge status="deploying" />);

    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    expect(screen.getByText("deploying")).toBeInTheDocument();
  });

  it("renders spinner with 'pending' label for awaiting states", () => {
    render(<StatusBadge status="awaiting_deployment" />);

    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
  });

  it("renders error icon for failed status", () => {
    render(<StatusBadge status="deployment_failed" resource={mockResource} />);

    // For failed status, it shows the tooltip host and font icon
    const tooltipHost = screen.getByTestId("tooltip");
    expect(tooltipHost).toBeInTheDocument();

    // The FontIcon should be inside the tooltip host
    const errorIcon = screen.getByTestId("font-icon");
    expect(errorIcon).toBeInTheDocument();
    expect(errorIcon).toHaveAttribute("data-icon-name", "AlertSolid");
  });

  it("renders disabled icon for disabled resource", () => {
    const disabledResource = {
      ...mockResource,
      isEnabled: false,
    };

    render(<StatusBadge status="deployed" resource={disabledResource} />);

    const disabledIcon = screen.getByTestId("font-icon");
    expect(disabledIcon).toBeInTheDocument();
    expect(disabledIcon).toHaveAttribute("data-icon-name", "Blocked2Solid");

    // Check tooltip host
    const tooltipHost = screen.getByTestId("tooltip");
    expect(tooltipHost).toHaveAttribute("title", "This resource is disabled");
  });

  it("renders nothing for successful status with enabled resource", () => {
    render(<StatusBadge status="deployed" resource={mockResource} />);

    // Should not render any icons or spinners
    expect(screen.queryByTestId("spinner")).not.toBeInTheDocument();
    expect(screen.queryByTestId("icon-AlertSolid")).not.toBeInTheDocument();
    expect(screen.queryByTestId("icon-Blocked2Solid")).not.toBeInTheDocument();
  });

  it("renders nothing for unknown status", () => {
    render(<StatusBadge status="unknown_status" />);

    expect(screen.queryByTestId("spinner")).not.toBeInTheDocument();
    expect(screen.queryByTestId("icon-AlertSolid")).not.toBeInTheDocument();
    expect(screen.queryByTestId("icon-Blocked2Solid")).not.toBeInTheDocument();
  });

  it("replaces underscores with spaces in status text", () => {
    render(<StatusBadge status="invoking_action" />);

    // For in-progress states, it should show the spinner with formatted text
    expect(screen.getByTestId("spinner")).toBeInTheDocument();
    expect(screen.getByText("invoking action")).toBeInTheDocument();
  });

  it("shows detailed error tooltip for failed status", () => {
    render(<StatusBadge status="deployment_failed" resource={mockResource} />);

    const tooltipHost = screen.getByTestId("tooltip");
    expect(tooltipHost).toBeInTheDocument();

    // The error icon should be present with the correct icon name
    const errorIcon = screen.getByTestId("font-icon");
    expect(errorIcon).toBeInTheDocument();
    expect(errorIcon).toHaveAttribute("data-icon-name", "AlertSolid");
    expect(errorIcon).toHaveAttribute("aria-describedby", "item-test-resource-id-failed");
  });
});
