/**
 * Schema Upgrade Utility Functions
 * Helper utilities for comparing JSON Schemas, resolving dotted paths,
 * evaluating allOf conditions, and building reduced forms during resource upgrades.
 */

// Utility to check if a path part name is a prototype property
export const partGuard = (part: string): boolean =>
  part === "__proto__" || part === "constructor" || part === "prototype";

export const clonePropertyValues = <T>(value: T): T => {
  if (typeof structuredClone === "function") {
    return structuredClone(value);
  }
  return JSON.parse(JSON.stringify(value)) as T;
};

// Utility to get all property keys from template schema's properties object recursively, flattening nested if needed
export const getAllPropertyKeys = (properties: any, prefix = "", data: any = undefined): string[] => {
  if (!properties) return [];
  let keys: string[] = [];
  for (const [key, value] of Object.entries(properties)) {
    if (partGuard(key)) continue;
    const currentData = data && typeof data === "object" ? data[key] : undefined;
    if (value && typeof value === "object" && (value as any).items && typeof (value as any).items === "object") {
      keys.push(prefix + key);
      if (Array.isArray(currentData) && (value as any).items.properties) {
        currentData.forEach((_item: any, index: number) => {
          keys = keys.concat(getAllPropertyKeys((value as any).items.properties, `${prefix + key}.${index}.`, _item));
        });
      }
    } else if (value && typeof value === "object" && "properties" in value) {
      // Include the object container itself so required-object detection works, then recurse into children.
      // Array item properties are traversed with indexed paths such as "items.0.value".
      keys.push(prefix + key);
      keys = keys.concat(getAllPropertyKeys((value as any)["properties"], prefix + key + ".", currentData));
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
const cloneArrayValuesForSchema = (value: any[], schema: any): any[] => {
  if (!schema?.items || !Array.isArray(value)) return clonePropertyValues(value);

  return value.map((item) => {
    if (!item || typeof item !== "object" || Array.isArray(item) || !schema.items.properties) {
      return clonePropertyValues(item);
    }
    const filteredItem: Record<string, any> = {};
    for (const key of Object.keys(schema.items.properties)) {
      if (partGuard(key) || item[key] === undefined) continue;
      filteredItem[key] = clonePropertyValues(item[key]);
    }
    return filteredItem;
  });
};

export const setNestedValue = (obj: any, path: string, value: any, source?: any, sourceSchema?: any): void => {
  const parts = path.split(".");
  let current = obj;
  let currentSource = source;
  let currentSchema = sourceSchema;
  for (let i = 0; i < parts.length - 1; i++) {
    const part = parts[i];
    if (partGuard(part)) {
      return;
    }
    const sourceValue = currentSource && typeof currentSource === "object" ? currentSource[part] : undefined;
    if (!(part in current) || typeof current[part] !== "object" || current[part] === null) {
      current[part] = Array.isArray(sourceValue)
        ? cloneArrayValuesForSchema(sourceValue, currentSchema?.properties?.[part] ?? currentSchema?.items)
        : {};
    }
    current = current[part];
    currentSource = sourceValue;
    currentSchema = currentSchema?.properties?.[part] ?? currentSchema?.items;
  }
  const lastPart = parts[parts.length - 1];
  if (!partGuard(lastPart)) {
    current[lastPart] = value;
  }
};

// Utility to deeply merge two property objects (e.g. existing resource properties and new property values)
export const mergePropertyValues = (existing: any, updated: any): any => {
  if (!existing || typeof existing !== "object") return updated || {};
  if (!updated || typeof updated !== "object") return existing || {};
  const result: any = { ...existing };
  for (const key of Object.keys(updated)) {
    if (partGuard(key)) continue;
    if (
      updated[key] &&
      typeof updated[key] === "object" &&
      !Array.isArray(updated[key]) &&
      existing[key] &&
      typeof existing[key] === "object" &&
      !Array.isArray(existing[key])
    ) {
      result[key] = mergePropertyValues(existing[key], updated[key]);
    } else {
      result[key] = updated[key];
    }
  }
  return result;
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
    if (/^\d+$/.test(part)) {
      continue;
    }
    if (!current || !current[part]) return null;
    if (i === parts.length - 1) {
      return current[part];
    }
    if (current[part].items && /^\d+$/.test(parts[i + 1])) {
      current = current[part].items.properties || current[part].items;
    } else if (current[part].properties) {
      current = current[part].properties;
    } else {
      return null;
    }
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

    if (/^\d+$/.test(part) && currentSchema.items) {
      currentSchema = currentSchema.items;
      currState = currState ? currState[part] : undefined;
      continue;
    }

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

    let nextSchema = currentSchema.properties ? currentSchema.properties[part] : undefined;
    if (!nextSchema && currentSchema.allOf) {
      for (const condition of currentSchema.allOf) {
        const branch = matchesIfCondition(condition.if, currState) ? condition.then : condition.else;
        if (branch?.properties?.[part]) {
          nextSchema = branch.properties[part];
          break;
        }
      }
    }
    currentSchema = nextSchema;
    currState = currState ? currState[part] : undefined;
  }
  return false;
};

/**
 * Recursively prunes an object schema node to only include properties
 * that match or are prefixes of active property keys.
 */
export const pruneSchemaNode = (schemaNode: any, activeKeys: string[]): any => {
  if (!schemaNode || typeof schemaNode !== "object") {
    return schemaNode;
  }

  if (!schemaNode.properties || typeof schemaNode.properties !== "object") {
    return { ...schemaNode };
  }

  const prunedProperties: Record<string, any> = Object.create(null);
  const prunedRequired: string[] = [];
  const activeKeySet = new Set(activeKeys);
  const matchingSubKeysByProperty = new Map<string, string[]>();

  for (const activeKey of activeKeys) {
    const separatorIndex = activeKey.indexOf(".");
    if (separatorIndex === -1) continue;

    const propName = activeKey.slice(0, separatorIndex);
    const subKey = activeKey.slice(separatorIndex + 1);
    const matchingSubKeys = matchingSubKeysByProperty.get(propName) ?? [];
    matchingSubKeys.push(subKey);
    matchingSubKeysByProperty.set(propName, matchingSubKeys);
  }

  for (const [propName, propSchema] of Object.entries(schemaNode.properties)) {
    if (partGuard(propName)) continue;

    const exactMatch = activeKeySet.has(propName);
    const matchingSubKeys = matchingSubKeysByProperty.get(propName) ?? [];

    if (exactMatch || matchingSubKeys.length > 0) {
      if (
        matchingSubKeys.length > 0 &&
        propSchema &&
        typeof propSchema === "object" &&
        (propSchema as any).items?.properties
      ) {
        const itemKeys = matchingSubKeys.filter((key) => /^\d+\./.test(key)).map((key) => key.replace(/^\d+\./, ""));
        prunedProperties[propName] = {
          ...(propSchema as any),
          items: pruneSchemaNode((propSchema as any).items, itemKeys),
        };
      } else if (
        matchingSubKeys.length > 0 &&
        propSchema &&
        typeof propSchema === "object" &&
        (propSchema as any).properties
      ) {
        prunedProperties[propName] = pruneSchemaNode(propSchema, matchingSubKeys);
      } else {
        prunedProperties[propName] = { ...(propSchema as any) };
      }

      if (Array.isArray(schemaNode.required) && schemaNode.required.includes(propName)) {
        prunedRequired.push(propName);
      }
    }
  }

  const result: any = {
    ...schemaNode,
    properties: prunedProperties,
  };

  if (prunedRequired.length > 0) {
    result.required = prunedRequired;
  } else {
    delete result.required;
  }

  return result;
};

// Utility to build a reduced schema with only given keys, recursively pruning object schemas
export const buildReducedSchema = (fullSchema: any, keys: string[]): any => {
  if (!fullSchema || !fullSchema.properties) return null;
  return pruneSchemaNode(fullSchema, keys);
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
export const getAllPropertyKeysFromTemplate = (template: any, data: any = undefined): string[] => {
  if (!template) return [];
  let keys = getAllPropertyKeys(template.properties, "", data);

  if (template.allOf) {
    template.allOf.forEach((condition: any) => {
      if (condition.then && condition.then.properties) {
        keys = keys.concat(getAllPropertyKeys(condition.then.properties, "", data));
      }
      if (condition.else && condition.else.properties) {
        keys = keys.concat(getAllPropertyKeys(condition.else.properties, "", data));
      }
    });
  }
  return [...new Set(keys)];
};

// Include properties from branches controlled by any of the supplied keys so a selector change can activate them.
export const getConditionalPropertyKeysForTriggers = (template: any, triggerKeys: string[]): string[] => {
  if (!template?.allOf || triggerKeys.length === 0) return [];

  const triggerTopKeys = new Set(triggerKeys.map((key) => key.split(".")[0]));
  const dependentKeys: string[] = [];

  template.allOf.forEach((condition: any) => {
    const conditionalKeys = collectConditionalKeys(condition);
    if (!conditionalKeys.some((key) => triggerTopKeys.has(key.split(".")[0]))) return;

    if (condition.then?.properties) {
      dependentKeys.push(...getAllPropertyKeys(condition.then.properties));
    }
    if (condition.else?.properties) {
      dependentKeys.push(...getAllPropertyKeys(condition.else.properties));
    }
  });

  return [...new Set(dependentKeys)];
};

// Helper to extract top-level keys (matching backend removal checks)
export const getTopLevelKeysFromTemplate = (template: any): string[] => {
  if (!template) return [];
  let keys = Object.keys(template.properties || {}).filter((k) => !partGuard(k));
  if (template.allOf) {
    template.allOf.forEach((condition: any) => {
      if (condition.then && condition.then.properties) {
        keys = keys.concat(Object.keys(condition.then.properties).filter((k) => !partGuard(k)));
      }
      if (condition.else && condition.else.properties) {
        keys = keys.concat(Object.keys(condition.else.properties).filter((k) => !partGuard(k)));
      }
    });
  }
  return [...new Set(keys)];
};

// Helper to determine if a property key is defined on an active branch of the template for the given state
export const isKeyActiveInTemplate = (template: any, path: string, state: any): boolean => {
  if (!template) return false;
  // If property is defined in top-level properties, it's active
  if (getSchemaPropertyFromProperties(template.properties, path)) {
    return true;
  }
  // If property is defined in allOf, check matching branch
  if (template.allOf) {
    for (const condition of template.allOf) {
      const matchesIf = matchesIfCondition(condition.if, state);
      if (matchesIf && condition.then && condition.then.properties) {
        if (getSchemaPropertyFromProperties(condition.then.properties, path)) {
          return true;
        }
      } else if (!matchesIf && condition.else && condition.else.properties) {
        if (getSchemaPropertyFromProperties(condition.else.properties, path)) {
          return true;
        }
      }
    }
  }
  return false;
};
