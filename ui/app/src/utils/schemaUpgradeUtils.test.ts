import { describe, expect, it } from "vitest";
import {
  extractConditionalBlocks,
  getAllPropertyKeysFromTemplate,
  getSchemaProperty,
  isKeyActiveInTemplate,
  isPropertyRequiredInState,
  pruneSchemaNode,
  setNestedValue,
} from "./schemaUpgradeUtils";

describe("schema upgrade utilities", () => {
  it("evaluates required properties in the matching allOf branch", () => {
    const schema = {
      properties: {
        mode: { type: "string" },
        conditional_property: { type: "string" },
      },
      allOf: [
        {
          if: { properties: { mode: { const: "then" } } },
          then: { required: ["conditional_property"] },
          else: { required: ["mode"] },
        },
      ],
    };

    expect(isPropertyRequiredInState(schema, "conditional_property", { mode: "then" })).toBe(true);
    expect(isPropertyRequiredInState(schema, "conditional_property", { mode: "else" })).toBe(false);
    expect(isPropertyRequiredInState(schema, "mode", { mode: "else" })).toBe(true);
  });

  it("prunes nested properties and required fields", () => {
    const schema = {
      type: "object",
      properties: {
        parent: {
          type: "object",
          properties: {
            kept: { type: "string" },
            removed: { type: "string" },
          },
          required: ["kept", "removed"],
        },
        removed_top_level: { type: "string" },
      },
      required: ["parent", "removed_top_level"],
    };

    expect(pruneSchemaNode(schema, ["parent.kept"])).toEqual({
      type: "object",
      properties: {
        parent: {
          type: "object",
          properties: { kept: { type: "string" } },
          required: ["kept"],
        },
      },
      required: ["parent"],
    });
  });

  it("does not extract conditionals when a new key is only declared in a branch", () => {
    const conditional = {
      if: { properties: { selector: { const: "enabled" } } },
      then: { required: ["new_property"] },
    };
    const schema = { allOf: [conditional] };

    expect(extractConditionalBlocks(schema, ["new_property"])).toEqual({ allOf: [] });
  });

  it("keeps only target schema fields when cloning an upgrade array", () => {
    const result: Record<string, any> = {};
    const formData = { items: [{ old_field: "removed", new_field: "kept" }] };
    const targetSchema = {
      properties: {
        items: {
          type: "array",
          items: { type: "object", properties: { new_field: { type: "string" } } },
        },
      },
    };

    setNestedValue(result, "items.0.new_field", "kept", formData, targetSchema);

    expect(result).toEqual({ items: [{ new_field: "kept" }] });
  });

  it("discovers properties in nested conditional branches", () => {
    const schema = {
      properties: {
        parent: {
          type: "object",
          properties: { selector: { type: "string" } },
          allOf: [
            {
              if: { properties: { selector: { const: "enabled" } } },
              then: { properties: { conditional: { type: "string" } } },
            },
          ],
        },
      },
    };

    expect(getAllPropertyKeysFromTemplate(schema)).toContain("parent.conditional");
  });

  it("resolves nested conditional properties and active branches", () => {
    const schema = {
      properties: {
        parent: {
          type: "object",
          properties: { selector: { type: "string" } },
          allOf: [
            {
              if: { properties: { selector: { const: "enabled" } } },
              then: { properties: { conditional: { type: "string" } } },
              else: { properties: { other: { type: "string" } } },
            },
          ],
        },
      },
    };

    expect(getSchemaProperty(schema, "parent.conditional")).toEqual({ type: "string" });
    expect(isKeyActiveInTemplate(schema, "parent.conditional", { parent: { selector: "enabled" } })).toBe(true);
    expect(isKeyActiveInTemplate(schema, "parent.conditional", { parent: { selector: "disabled" } })).toBe(false);
  });

  it("recursively filters nested array item values by the target schema", () => {
    const result: Record<string, any> = {};
    const formData = {
      items: [{ nested: { kept: "yes", removed: "no" }, removed: "no" }],
    };
    const targetSchema = {
      properties: {
        items: {
          type: "array",
          items: {
            type: "object",
            properties: {
              nested: { type: "object", properties: { kept: { type: "string" } } },
            },
          },
        },
      },
    };

    setNestedValue(result, "items.0.nested.kept", "yes", formData, targetSchema);

    expect(result).toEqual({ items: [{ nested: { kept: "yes" } }] });
  });
});
