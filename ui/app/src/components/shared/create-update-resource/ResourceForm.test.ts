// Unit tests for ResourceForm logic
// Tests the removeReadOnlyProps function behavior with empty values

import { describe, it, expect } from "vitest";
import { ResourceTemplate } from "../../../models/resourceTemplate";

// Extracted logic from ResourceForm for testing
const removeReadOnlyProps = (data: any, template: ResourceTemplate): any => {
  // flatten all the nested properties from across the template into a basic array we can iterate easily
  let allProps = {} as any;

  const recurseTemplate = (templateFragment: any) => {
    Object.keys(templateFragment).forEach((key) => {
      if (key === "properties") {
        Object.keys(templateFragment[key]).forEach((prop) => {
          allProps[prop] = templateFragment[key][prop];
        });
      }
      if (typeof templateFragment[key] === "object" && key !== "if") {
        recurseTemplate(templateFragment[key]);
      }
    });
  };

  recurseTemplate(template);

  // iterate the data payload
  for (let prop in data) {
    // if the prop isn't in the template, or it's readOnly, delete it
    if (!allProps[prop] || allProps[prop].readOnly === true) {
      delete data[prop];
    }
  }

  return data;
};

describe("ResourceForm removeReadOnlyProps", () => {
  const mockTemplate = {
    id: "test-template",
    name: "test-template",
    type: "object",
    description: "Test template",
    version: "1.0.0",
    title: "Test Template",
    resourceType: "workspace" as any,
    current: true,
    properties: {
      display_name: {
        type: "string",
        title: "Display Name",
        readOnly: false,
      },
      description: {
        type: "string",
        title: "Description",
        readOnly: false,
      },
      billing_code: {
        type: "string",
        title: "Billing Code",
        readOnly: false,
      },
      readonly_field: {
        type: "string",
        title: "Read Only Field",
        readOnly: true,
      },
    },
    system_properties: {},
    actions: [],
    customActions: [],
    required: [],
    uiSchema: {},
    pipeline: {},
  } as ResourceTemplate;

  it("should keep fields with non-empty values", () => {
    const data = {
      display_name: "Test Workspace",
      description: "A test workspace",
      billing_code: "ABC123",
    };

    const result = removeReadOnlyProps({ ...data }, mockTemplate);

    expect(result).toEqual(data);
    expect(result.display_name).toBe("Test Workspace");
    expect(result.description).toBe("A test workspace");
    expect(result.billing_code).toBe("ABC123");
  });

  it("should keep fields with empty string values", () => {
    const data = {
      display_name: "Test Workspace",
      description: "",
      billing_code: "",
    };

    const result = removeReadOnlyProps({ ...data }, mockTemplate);

    expect(result).toEqual(data);
    expect(result.display_name).toBe("Test Workspace");
    expect(result.description).toBe("");
    expect(result.billing_code).toBe("");
    expect("description" in result).toBe(true);
    expect("billing_code" in result).toBe(true);
  });

  it("should remove read-only fields", () => {
    const data = {
      display_name: "Test Workspace",
      description: "A test workspace",
      readonly_field: "This should be removed",
    };

    const result = removeReadOnlyProps({ ...data }, mockTemplate);

    expect(result.display_name).toBe("Test Workspace");
    expect(result.description).toBe("A test workspace");
    expect("readonly_field" in result).toBe(false);
  });

  it("should remove fields not in template", () => {
    const data = {
      display_name: "Test Workspace",
      description: "A test workspace",
      extra_field: "This should be removed",
    };

    const result = removeReadOnlyProps({ ...data }, mockTemplate);

    expect(result.display_name).toBe("Test Workspace");
    expect(result.description).toBe("A test workspace");
    expect("extra_field" in result).toBe(false);
  });

  it("should handle update scenario with cleared fields", () => {
    // Simulate an update where a field that had a value is now cleared
    const data = {
      display_name: "Updated Workspace",
      description: "Updated description",
      billing_code: "", // User cleared this field
    };

    const result = removeReadOnlyProps({ ...data }, mockTemplate);

    expect(result.display_name).toBe("Updated Workspace");
    expect(result.description).toBe("Updated description");
    expect(result.billing_code).toBe("");
    expect("billing_code" in result).toBe(true); // Empty string should be kept
  });

  it("should keep all editable empty fields when updating", () => {
    // Scenario: User cleared multiple fields
    const data = {
      display_name: "",
      description: "",
      billing_code: "",
    };

    const result = removeReadOnlyProps({ ...data }, mockTemplate);

    expect("display_name" in result).toBe(true);
    expect("description" in result).toBe(true);
    expect("billing_code" in result).toBe(true);
    expect(result.display_name).toBe("");
    expect(result.description).toBe("");
    expect(result.billing_code).toBe("");
  });
});
