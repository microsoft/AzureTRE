# Pipeline Template Schema
This document will help you write a valid `pipeline: {}` block in your template.

> For a working example, see `./templates/workspace_services/guacamole/user_resources/guacamole-dev-vm/template_schema.json`.

## Schema
```json
"pipeline": {
    "install": [ // <-- currently only install supported
      {
        "stepId": "a unique string value here",
        "stepTitle": "Friendly description for the user here",
        "resourceTemplateName": "name of the resource template to update",
        "resourceType": "shared_service", // <-- currently only shared_service types supported
        "resourceAction": "upgrade", // <-- currently only upgrade supported
        "properties": [
        {
          "name": "display_name",
          "type": "string",
          "value": "A new name here!" // <-- currently only static strings supported 
        }]
      },
      {
        "stepId": "main" // <-- deployment of the VM resource
      },

```

## Notes
- Each step is executed in serial, in the order defined in the template
- Theoretically any number of steps could be created
- A step with `step_id` of `main` represents where in the chain the primary resource will get deployed. It is possible to omit this step altogether, and not touch the primary resource at all.
