import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getDefaultFormState, RJSFSchema } from "@rjsf/utils";
import { ResourceTemplate, sanitiseTemplateForRJSF } from "./resourceTemplate";
import { createResourceTemplateValidator } from "./resourceTemplateValidator";
import workspace from "../../../../templates/workspaces/base/template_schema.json";
import sharedService from "../../../../templates/shared_services/gitea/template_schema.json";
import firewall from "../../../../templates/shared_services/firewall/template_schema.json";
import workspaceService from "../../../../templates/workspace_services/guacamole/template_schema.json";
import foundry from "../../../../templates/workspace_services/ai-foundry/template_schema.json";
import userResource from "../../../../templates/workspace_services/guacamole/user_resources/guacamole-azure-linuxvm/template_schema.json";

const formSchema = (schema: unknown): RJSFSchema =>
  sanitiseTemplateForRJSF(structuredClone(schema) as ResourceTemplate) as RJSFSchema;

// Exercise the validator selection used by ResourceForm, without remote schema loading.
describe("resource template validation", () => {
  const fetch = vi.fn();
  let xhrOpen: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    fetch.mockReset().mockRejectedValue(new Error("Unexpected schema request"));
    vi.stubGlobal("fetch", fetch);
    xhrOpen = vi.spyOn(XMLHttpRequest.prototype, "open").mockImplementation(() => {
      throw new Error("Unexpected schema request");
    });
  });

  afterEach(() => {
    expect(fetch).not.toHaveBeenCalled();
    expect(xhrOpen).not.toHaveBeenCalled();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it.each([
    ["workspace", workspace],
    ["shared service", sharedService],
    ["firewall", firewall],
    ["workspace service", workspaceService],
    ["Foundry", foundry],
    ["user resource", userResource],
  ])("accepts the defaults from the checked-in %s template", (_name, template) => {
    const schema = formSchema(template);
    const validator = createResourceTemplateValidator(schema);
    const data = getDefaultFormState(validator, schema);
    expect(validator.validateFormData(data, schema).errors).toEqual([]);
  });

  it("preserves the Foundry default and validates explicit outbound allowlists", () => {
    const schema = formSchema(foundry);
    const validator = createResourceTemplateValidator(schema);
    const data = getDefaultFormState(validator, schema);
    expect(data.allowed_fqdns).toEqual(["deny-all.invalid"]);
    for (const allowed_fqdns of [[], ["deny-all.invalid"], ["learn.microsoft.com"]]) {
      expect(validator.validateFormData({ ...data, allowed_fqdns }, schema).errors).toEqual([]);
    }
    for (const allowed_fqdns of [null, ["https://example.com"], ["*.example.com"], ["example.com", "example.com"]]) {
      expect(validator.validateFormData({ ...data, allowed_fqdns }, schema).errors.length).toBeGreaterThan(0);
    }
  });

  it("enforces required fields, enums and conditional fields in existing templates", () => {
    const schema = formSchema(workspace);
    const validator = createResourceTemplateValidator(schema);
    expect(validator.validateFormData({}, schema).errors).toEqual(
      expect.arrayContaining([expect.objectContaining({ name: "required" })]),
    );
    const data = getDefaultFormState(validator, schema);
    expect(validator.validateFormData({ ...data, auth_type: "invalid" }, schema).errors).toEqual(
      expect.arrayContaining([expect.objectContaining({ name: "enum" })]),
    );
    expect(validator.validateFormData({ ...data, auth_type: "Manual" }, schema).errors).toEqual(
      expect.arrayContaining([expect.objectContaining({ name: "required", params: { missingProperty: "client_id" } })]),
    );
    expect(
      validator.validateFormData({ ...data, auth_type: "Manual", client_id: "test-client" }, schema).errors,
    ).toEqual([]);
  });

  it("resolves local references under a schema ID and validates nested arrays and formats", () => {
    const schema: RJSFSchema = {
      $id: "https://schemas.example.test/resources/form.json",
      type: "object",
      definitions: { address: { type: "string", format: "email" } },
      properties: {
        contacts: {
          type: "array",
          items: {
            type: "object",
            required: ["email"],
            properties: { email: { $ref: "#/definitions/address" } },
          },
        },
      },
    };
    const validator = createResourceTemplateValidator(schema);
    expect(validator.validateFormData({ contacts: [{ email: "owner@example.test" }] }, schema).errors).toEqual([]);
    expect(validator.validateFormData({ contacts: [{ email: "invalid" }] }, schema).errors).toEqual(
      expect.arrayContaining([expect.objectContaining({ name: "format" })]),
    );
    expect(validator.validateFormData({ contacts: [{}] }, schema).errors).toEqual(
      expect.arrayContaining([expect.objectContaining({ name: "required" })]),
    );
  });

  it.each([
    "https://schemas.example.test/missing.json",
    "%2f%2fexample.test:/schema",
    "http://[::not-valid]/schema",
    "http://%256c%256f%2563%2561%256c%2568%256f%2573%2574/schema",
    "//bücher.example/schema",
  ])("reports an unresolved reference without requesting %s", ($ref) => {
    const schema: RJSFSchema = {
      type: "object",
      properties: { value: { $ref } },
    };
    const result = createResourceTemplateValidator(schema).rawValidation(schema, { value: "test" });
    expect(result.validationError).toBeDefined();
  });
});
