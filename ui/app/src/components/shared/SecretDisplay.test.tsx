import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, createPartialFluentUIMock, mockClipboardAPI } from "../../test-utils";
import { mockUserResource, mockWorkspaceService } from "../../test-utils/mockData";

// Shared mock for the auth API call
const mockApiCall = vi.fn();
vi.mock("../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => mockApiCall,
  HttpMethod: { Get: "GET", Post: "POST", Patch: "PATCH", Delete: "DELETE" },
  ResultType: { JSON: "JSON", Text: "TEXT", None: "None" },
}));

// Mock ExceptionLayout so we can assert on error rendering
vi.mock("./ExceptionLayout", () => ({
  ExceptionLayout: ({ e }: any) => <div data-testid="exception-layout">{e?.userMessage || e?.message}</div>,
}));

// Mock FluentUI components using the centralized mock
vi.mock("@fluentui/react", async () => {
  const actual = await vi.importActual("@fluentui/react");
  return {
    ...actual,
    ...createPartialFluentUIMock(["Stack", "Text", "IconButton", "TooltipHost", "Spinner", "SpinnerSize"]),
  };
});

import { SecretDisplay } from "./SecretDisplay";

const secretResource = {
  ...mockWorkspaceService,
  properties: {
    admin_password_keyvault_secret_id: "https://kv.vault.azure.net/secrets/admin-password/abc",
  },
};

beforeEach(() => {
  mockClipboardAPI();
  mockApiCall.mockReset();
});

describe("SecretDisplay Component", () => {
  it("shows a masked placeholder and reveal button initially, without calling the API", () => {
    render(<SecretDisplay resource={secretResource} propertyName="admin_password_keyvault_secret_id" />);

    expect(screen.getByText("••••••••")).toBeInTheDocument();
    const revealButton = screen.getByLabelText("Show secret");
    expect(revealButton).toHaveAttribute("data-icon-name", "RedEye");
    expect(mockApiCall).not.toHaveBeenCalled();
  });

  it("retrieves and displays the secret value when reveal is clicked", async () => {
    mockApiCall.mockResolvedValue({ key: "admin_password_keyvault_secret_id", value: "s3cr3t-value" });

    render(<SecretDisplay resource={secretResource} propertyName="admin_password_keyvault_secret_id" />);

    fireEvent.click(screen.getByLabelText("Show secret"));

    await waitFor(() => {
      expect(screen.getByText("s3cr3t-value")).toBeInTheDocument();
    });

    expect(mockApiCall).toHaveBeenCalledWith(
      `${secretResource.resourcePath}/secrets/admin_password_keyvault_secret_id`,
      "GET",
      expect.anything(),
    );
  });

  it("calls the user resource secret endpoint using the resource path", async () => {
    mockApiCall.mockResolvedValue({ key: "vm_password_keyvault_secret_id", value: "abc" });
    const userResource = {
      ...mockUserResource,
      properties: { vm_password_keyvault_secret_id: "https://kv/secrets/vm/1" },
    };

    render(<SecretDisplay resource={userResource} propertyName="vm_password_keyvault_secret_id" />);
    fireEvent.click(screen.getByLabelText("Show secret"));

    await waitFor(() => expect(screen.getByText("abc")).toBeInTheDocument());
    expect(mockApiCall).toHaveBeenCalledWith(
      `${userResource.resourcePath}/secrets/vm_password_keyvault_secret_id`,
      "GET",
      expect.anything(),
    );
  });

  it("hides the secret again when the hide button is clicked", async () => {
    mockApiCall.mockResolvedValue({ key: "admin_password_keyvault_secret_id", value: "s3cr3t-value" });

    render(<SecretDisplay resource={secretResource} propertyName="admin_password_keyvault_secret_id" />);
    fireEvent.click(screen.getByLabelText("Show secret"));

    await waitFor(() => expect(screen.getByText("s3cr3t-value")).toBeInTheDocument());

    fireEvent.click(screen.getByLabelText("Hide secret"));

    expect(screen.queryByText("s3cr3t-value")).not.toBeInTheDocument();
    expect(screen.getByText("••••••••")).toBeInTheDocument();
  });

  it("copies the revealed secret to the clipboard", async () => {
    mockApiCall.mockResolvedValue({ key: "admin_password_keyvault_secret_id", value: "s3cr3t-value" });

    render(<SecretDisplay resource={secretResource} propertyName="admin_password_keyvault_secret_id" />);
    fireEvent.click(screen.getByLabelText("Show secret"));

    await waitFor(() => expect(screen.getByText("s3cr3t-value")).toBeInTheDocument());

    fireEvent.click(screen.getByLabelText("Copy secret to clipboard"));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("s3cr3t-value");
  });

  it("renders an error when the secret cannot be retrieved", async () => {
    mockApiCall.mockRejectedValue({ message: "not found" });

    render(<SecretDisplay resource={secretResource} propertyName="admin_password_keyvault_secret_id" />);
    fireEvent.click(screen.getByLabelText("Show secret"));

    await waitFor(() => {
      expect(screen.getByTestId("exception-layout")).toBeInTheDocument();
    });
    expect(screen.getByText("Error retrieving secret")).toBeInTheDocument();
    expect(screen.queryByText("s3cr3t-value")).not.toBeInTheDocument();
  });
});
