import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ResourceForm } from "./ResourceForm";
import { Resource } from "../../../models/resource";
import { ResourceType } from "../../../models/resourceType";

const { apiCall } = vi.hoisted(() => ({ apiCall: vi.fn() }));

vi.mock("../../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => apiCall,
  HttpMethod: { Get: "GET", Post: "POST", Patch: "PATCH" },
  ResultType: { JSON: "JSON" },
}));

const template = {
  name: "test-template",
  type: "object",
  title: "Resource",
  required: ["display_name", "endpoint"],
  properties: {
    display_name: { type: "string", title: "Name", minLength: 1 },
    description: { type: "string", title: "Description", default: "" },
    overview: { type: "string", title: "Overview", default: "" },
    endpoint: { type: "string", title: "Endpoint", format: "uri", default: "https://example.test/" },
    generated: { type: "string", title: "Generated value", readOnly: true, default: "server-value" },
  },
  uiSchema: { "ui:order": ["*"] },
};
const operation = { id: "test-operation" };
const templatePath = "/workspace-templates/test-template";
const properties = { display_name: "Research", description: "", overview: "", endpoint: "https://example.test/" };

// Keep Fluent UI, RJSF and the selected Ajv validator real. Only the TRE API boundary is mocked.
describe("ResourceForm validation and submission", () => {
  const fetch = vi.fn();
  let xhrOpen: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    apiCall
      .mockReset()
      .mockImplementation(async (_path, method) => (method === "GET" ? structuredClone(template) : { operation }));
    fetch.mockReset().mockRejectedValue(new Error("Unexpected network request"));
    vi.stubGlobal("fetch", fetch);
    xhrOpen = vi.spyOn(XMLHttpRequest.prototype, "open").mockImplementation(() => {
      throw new Error("Unexpected network request");
    });
  });

  afterEach(() => {
    cleanup();
    expect(fetch).not.toHaveBeenCalled();
    expect(xhrOpen).not.toHaveBeenCalled();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("blocks missing required fields and invalid URI input before submitting", async () => {
    const onCreateResource = vi.fn();
    const { container } = render(
      <ResourceForm
        templateName="test-template"
        templatePath={templatePath}
        resourcePath="/workspaces"
        onCreateResource={onCreateResource}
      />,
    );
    const name = await screen.findByRole("textbox", { name: /^Name/ });
    fireEvent.submit(container.querySelector("form")!);
    await screen.findAllByText(/required property/);
    expect(apiCall).toHaveBeenCalledTimes(1);
    expect(onCreateResource).not.toHaveBeenCalled();

    fireEvent.change(name, { target: { value: "Research" } });
    fireEvent.change(screen.getByRole("textbox", { name: /^Endpoint/ }), { target: { value: "not a URI" } });
    fireEvent.submit(container.querySelector("form")!);
    await screen.findAllByText(/must match format/);
    expect(apiCall).toHaveBeenCalledTimes(1);
    expect(onCreateResource).not.toHaveBeenCalled();
  });

  it("submits a valid create payload without read-only properties", async () => {
    const onCreateResource = vi.fn();
    const { container } = render(
      <ResourceForm
        templateName="test-template"
        templatePath={templatePath}
        resourcePath="/workspaces"
        onCreateResource={onCreateResource}
      />,
    );
    fireEvent.change(await screen.findByRole("textbox", { name: /^Name/ }), { target: { value: "Research" } });
    fireEvent.submit(container.querySelector("form")!);
    await waitFor(() => expect(onCreateResource).toHaveBeenCalledWith(operation));
    expect(apiCall).toHaveBeenNthCalledWith(1, templatePath, "GET");
    expect(apiCall).toHaveBeenNthCalledWith(
      2,
      "/workspaces",
      "POST",
      undefined,
      { templateName: "test-template", properties },
      "JSON",
    );
    expect(apiCall).toHaveBeenCalledTimes(2);
  });

  describe.each([undefined, "http://json-schema.org/draft-07/schema", "https://json-schema.org/draft/2020-12/schema"])(
    "schema dialect %s",
    ($schema) => {
      it.each([false, true])("renders local definitions and validates submission (update=%s)", async (isUpdate) => {
        const referencedTemplate = {
          ...template,
          ...($schema ? { $schema } : {}),
          $id: "https://example.test/resource-template.json",
          $defs: { label: { type: "string", title: "Name", minLength: 3 } },
          properties: { ...template.properties, display_name: { $ref: "#/$defs/label" } },
        };
        apiCall.mockImplementation(async (_path, method) =>
          method === "GET" ? structuredClone(referencedTemplate) : { operation },
        );
        const onCreateResource = vi.fn();
        const updateResource = isUpdate
          ? ({
              resourceType: ResourceType.Workspace,
              resourcePath: "/workspaces/workspace",
              templateVersion: "1.0.0",
              _etag: "test-etag",
              properties: { ...properties, generated: "server-value" },
            } as Resource)
          : undefined;
        const { container } = render(
          <ResourceForm
            templateName="test-template"
            templatePath={templatePath}
            resourcePath="/workspaces"
            updateResource={updateResource}
            onCreateResource={onCreateResource}
          />,
        );
        const name = await screen.findByRole("textbox", { name: /^Name/ });
        fireEvent.change(name, { target: { value: "x" } });
        fireEvent.submit(container.querySelector("form")!);
        await screen.findAllByText(/must NOT have fewer than 3 characters/);
        expect(apiCall).toHaveBeenCalledTimes(1);
        expect(onCreateResource).not.toHaveBeenCalled();

        fireEvent.change(name, { target: { value: "Research" } });
        fireEvent.submit(container.querySelector("form")!);
        await waitFor(() => expect(onCreateResource).toHaveBeenCalledWith(operation));
        expect(apiCall).toHaveBeenCalledTimes(2);
        const submitted = apiCall.mock.calls[1];
        expect(submitted[0]).toBe(isUpdate ? "/workspaces/workspace" : "/workspaces");
        expect(submitted[1]).toBe(isUpdate ? "PATCH" : "POST");
        expect(submitted[3]).toEqual(isUpdate ? { properties } : { templateName: "test-template", properties });
        if (isUpdate) expect(submitted[7]).toBe("test-etag");
      });
    },
  );

  it.each([
    [ResourceType.Workspace, "/workspaces/workspace", undefined],
    [ResourceType.SharedService, "/shared-services/service", undefined],
    [ResourceType.WorkspaceService, "/workspaces/workspace/workspace-services/service", "api://workspace"],
    [
      ResourceType.UserResource,
      "/workspaces/workspace/workspace-services/service/user-resources/user",
      "api://workspace",
    ],
  ])("preserves the update payload, ETag and API scope for %s", async (resourceType, resourcePath, expectedScope) => {
    const onCreateResource = vi.fn();
    const updateResource = {
      resourceType,
      resourcePath,
      templateVersion: "1.0.0",
      _etag: "test-etag",
      properties: { ...properties, display_name: "Previous name", generated: "server-value", obsolete: "removed" },
    } as Resource;
    const { container } = render(
      <ResourceForm
        templateName="test-template"
        templatePath={templatePath}
        resourcePath="/unused"
        updateResource={updateResource}
        workspaceApplicationIdURI="api://workspace"
        onCreateResource={onCreateResource}
      />,
    );
    const name = await screen.findByRole("textbox", { name: /^Name/ });
    expect(name).toHaveValue("Previous name");
    fireEvent.change(name, { target: { value: "Research" } });
    fireEvent.submit(container.querySelector("form")!);
    await waitFor(() => expect(onCreateResource).toHaveBeenCalledWith(operation));
    expect(apiCall).toHaveBeenNthCalledWith(1, `${templatePath}?is_update=true&version=1.0.0`, "GET");
    expect(apiCall).toHaveBeenNthCalledWith(
      2,
      resourcePath,
      "PATCH",
      expectedScope,
      { properties },
      "JSON",
      undefined,
      undefined,
      "test-etag",
    );
    expect(apiCall).toHaveBeenCalledTimes(2);
  });
});
