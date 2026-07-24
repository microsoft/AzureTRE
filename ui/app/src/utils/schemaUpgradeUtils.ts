/**
 * Schema Upgrade Utility Functions
 * Helper utilities for comparing JSON Schemas, resolving dotted paths,
 * evaluating allOf conditions, and building reduced forms during resource upgrades.
 */

// Utility to check if a path part name is a prototype property
export const partGuard = (part: string): boolean =>
  part === "__proto__" || part === "constructor" || part === "prototype";

// Utility to get all property keys from template schema's properties object recursively, flattening nested if needed
export const getAllPropertyKeys = (properties: any, prefix = ""): string[] => {
  if (!properties) return [];
  let keys: string[] = [];
  for (const [key, value] of Object.entries(properties)) {
    if (value && typeof value === "object" && "properties" in value) {
      // recur for nested properties
      keys = keys.concat(getAllPropertyKeys((value as any)["properties"], prefix + key + "."));
    } else {
      keys.push(prefix + key);
    }
  }
  return keys;
};

// Utility to get a nested value from an object using a dotted path (e.g. "parent.child")
export const getNestedValue = (obj: any, path: string): any => {
  const parts = path.split(".");
  let current = obj;
  for (const part of parts) {
    if (partGuard(part)) {
      return undefined;
    }
    if (current === null || current === undefined) return undefined;
    current = current[part];
  }
  return current;
};

// Utility to set a nested value in an object using a dotted path (e.g. "parent.sibling")
export const setNestedValue = (obj: any, path: string, value: any): void => {
  const parts = path.split(".");
  let current = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    const part = parts[i];
    if (partGuard(part)) {
      return;
    }
    if (!(part in current) || typeof current[part] !== "object" || current[part] === null) {
      current[part] = {};
    }
    current = current[part];
  }
  const lastPart = parts[parts.length - 1];
  if (!partGuard(lastPart)) {
    current[lastPart] = value;
  }
};

// Utility to get schema property from properties object using a dotted path
export const getSchemaPropertyFromProperties = (properties: any, path: string): any => {
  const parts = path.split(".");
  let current = properties;
  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    if (partGuard(part)) {
      return null;
    }
    if (!current || !current[part]) return null;
    if (i === parts.length - 1) {
      return current[part];
    }
    current = current[part].properties;
  }
  return null;
};

// Utility to get schema property from template (both properties and allOf) using a dotted path
export const getSchemaProperty = (template: any, path: string): any => {
  if (!template) return null;

  let prop = getSchemaPropertyFromProperties(template.properties, path);
  if (prop) return prop;

  if (template.allOf) {
    for (const condition of template.allOf) {
      if (condition.then && condition.then.properties) {
        prop = getSchemaPropertyFromProperties(condition.then.properties, path);
        if (prop) return prop;
      }
      if (condition.else && condition.else.properties) {
        prop = getSchemaPropertyFromProperties(condition.else.properties, path);
        if (prop) return prop;
      }
    }
  }
  return null;
};

// Utility to get nested uiSchema object using a dotted path
export const getNestedUiSchema = (uiSchema: any, path: string): any => {
  const parts = path.split(".");
  let current = uiSchema;
  for (const part of parts) {
    if (partGuard(part)) {
      return undefined;
    }
    if (current === null || current === undefined) return undefined;
    current = current[part];
  }
  return current;
};

// Utility to check if a simple JSON Schema condition matches the current state
export const matchesIfCondition = (ifSchema: any, state: any): boolean => {
  if (!ifSchema || !ifSchema.properties) return false;
  for (const [key, cond] of Object.entries(ifSchema.properties)) {
    const val = getNestedValue(state, key);
    if (cond && typeof cond === "object") {
      if ("const" in (cond as any)) {
        if (val !== (cond as any).const) return false;
      } else if ("enum" in (cond as any) && Array.isArray((cond as any).enum)) {
        if (!(cond as any).enum.includes(val)) return false;
      } else {
        // treat only undefined/null as missing; allow false, 0, and empty string as valid values
        if (val === undefined || val === null) return false;
      }
    } else {
      // treat only undefined/null as missing; allow false, 0, and empty string as valid values
      if (val === undefined || val === null) return false;
    }
  }
  return true;
};

// Utility to check if a nested property (dotted path) is required in the schema given the current form state
export const isPropertyRequiredInState = (templateSchema: any, path: string, state: any): boolean => {
  if (!templateSchema) return false;

  const parts = path.split(".");
  let currentSchema = templateSchema;
  let currState = state;

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    if (!currentSchema) return false;

    let isPartRequired = currentSchema.required && currentSchema.required.includes(part);

    if (currentSchema.allOf) {
      for (const condition of currentSchema.allOf) {
        if (matchesIfCondition(condition.if, currState)) {
          if (condition.then && condition.then.required && condition.then.required.includes(part)) {
            isPartRequired = true;
          }
        } else {
          if (condition.else && condition.else.required && condition.else.required.includes(part)) {
            isPartRequired = true;
          }
        }
      }
    }

    if (i === parts.length - 1) {
      return !!isPartRequired;
    }

    const isPartPresent = currState && currState[part] !== undefined && currState[part] !== null;
    if (!isPartRequired && !isPartPresent) {
      return false;
    }

    currentSchema = currentSchema.properties ? currentSchema.properties[part] : undefined;
    currState = currState ? currState[part] : undefined;
  }
  return false;
};

// Utility to build a reduced schema with only given keys and their nested schema (depth 1), including required
export const buildReducedSchema = (fullSchema: any, keys: string[]): any => {
  if (!fullSchema || !fullSchema.properties) return null;
  const reducedProperties: any = {};
  const required: string[] = [];

  keys.forEach((key) => {
    // Only allow top-level property keys (no nested with dots) for simplicity here
    const topKey = key.split(".")[0];
    if (fullSchema.properties[topKey]) {
      if (!reducedProperties[topKey]) {
        reducedProperties[topKey] = fullSchema.properties[topKey];
        if (fullSchema.required && fullSchema.required.includes(topKey)) {
          required.push(topKey);
        }
      }
    }
  });

  return {
    type: "object",
    properties: reducedProperties,
    required: required.length > 0 ? required : undefined,
  };
};

// Utility to collect direct property keys referenced inside conditional schemas
export const collectConditionalKeys = (entry: any): string[] => {
  const keys: string[] = [];
  if (!entry) return keys;
  const collect = (schemaPart: any) => {
    if (!schemaPart) return;
    // collect any property names declared under a properties block
    if (schemaPart.properties) {
      keys.push(...Object.keys(schemaPart.properties));
    }
    // also collect any property names declared as required (common pattern where
    // a conditional only sets then.required / else.required without redefining
    // the property's schema under then/else.properties)
    if (Array.isArray(schemaPart.required)) {
      keys.push(...schemaPart.required.filter((r: unknown): r is string => typeof r === "string"));
    }
  };
  collect(entry.if);
  collect(entry.then);
  collect(entry.else);
  return [...new Set(keys)];
};

// Extract conditional blocks that reference any of the new properties.
export const extractConditionalBlocks = (schema: any, newKeys: string[]) => {
  const conditionalEntries: any[] = [];
  if (!schema) return { allOf: [] };
  const allOf = schema.allOf || [];
  // precompute top-level names for the new keys
  const newTopKeys = new Set(newKeys.map((nk) => (typeof nk === "string" ? nk.split(".")[0] : nk)));
  allOf.forEach((entry: any) => {
    if (entry && entry.if) {
      const conditionalKeys = collectConditionalKeys(entry);
      const conditionalTopKeys = conditionalKeys.map((k) => (typeof k === "string" ? k.split(".")[0] : k));
      // include entry if any top-level conditional key matches a top-level new key
      if (conditionalTopKeys.some((ck) => newTopKeys.has(ck))) {
        conditionalEntries.push(entry);
      }
    }
  });
  return { allOf: conditionalEntries };
};

// Helper to extract all property keys from template properties and allOf conditionals
export const getAllPropertyKeysFromTemplate = (template: any): string[] => {
  if (!template) return [];
  let keys = getAllPropertyKeys(template.properties);

  if (template.allOf) {
    template.allOf.forEach((condition: any) => {
      if (condition.then && condition.then.properties) {
        keys = keys.concat(getAllPropertyKeys(condition.then.properties));
      }
      if (condition.else && condition.else.properties) {
        keys = keys.concat(getAllPropertyKeys(condition.else.properties));
      }
    });
  }
  return [...new Set(keys)];
};

// Helper to extract top-level keys (matching backend removal checks)
export const getTopLevelKeysFromTemplate = (template: any): string[] => {
  if (!template) return [];
  let keys = Object.keys(template.properties || {});
  if (template.allOf) {
    template.allOf.forEach((condition: any) => {
      if (condition.then && condition.then.properties) {
        keys = keys.concat(Object.keys(condition.then.properties));
      }
      if (condition.else && condition.else.properties) {
        keys = keys.concat(Object.keys(condition.else.properties));
      }
    });
  }
  return [...new Set(keys)];
};
