import { describe, expect, it } from "vitest";
import { extractConditionalBlocks, isPropertyRequiredInState, pruneSchemaNode } from "./schemaUpgradeUtils";

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

  it("extracts conditionals when a referenced key appears only in required", () => {
    const conditional = {
      if: { properties: { selector: { const: "enabled" } } },
      then: { required: ["new_property"] },
    };
    const schema = { allOf: [conditional] };

    expect(extractConditionalBlocks(schema, ["new_property"])).toEqual({ allOf: [conditional] });
  });
});
