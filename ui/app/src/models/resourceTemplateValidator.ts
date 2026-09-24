import { customizeValidator } from "@rjsf/validator-ajv8";
import { RJSFSchema } from "@rjsf/utils";
import Ajv2020 from "ajv/dist/2020";

export const createResourceTemplateValidator = (schema: RJSFSchema | null) => {
  // Keep separate instances for each form, dialect and template version.
  // Templates stored without a dialect retain the existing Draft 7 UI behaviour.
  const isDraft202012 = schema?.$schema?.replace(/#$/, "") === "https://json-schema.org/draft/2020-12/schema";
  return customizeValidator(isDraft202012 ? { AjvClass: Ajv2020 } : {});
};
