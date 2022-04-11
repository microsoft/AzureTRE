# Pipeline Template Schema
This document will help you write a valid `pipeline: {}` block in your template. 

> For a working example, see `./templates/workspace_services/guacamole/user_resources/guacamole-dev-vm/template_schema.json`.

## Schema
```json
"pipeline": {
    "install": [ // <-- currently only install supported
      {
        "step_id": "a unique string value here",
        "resource_template_name": "name of the resource template to update",
        "resource_type": "shared_service", // <-- currently only shared_service types supported
        "resource_action": "upgrade", // <-- currently only upgrade supported
        "properties": [
        {
          "name": "display_name",
          "type": "string",
          "value": "A new name here!" // <-- currently only static strings supported 
        }]
      },
      {
        "step_id": "main" // <-- deployment of the VM resource
      },

```

## Notes:
- Each step is executed in serial, in the order defined in the template
- Theoretically any number of steps could be created
- A step with `step_id` of `main` represents where in the chain the primary resource will get deployed. It is possible to omit this step altogether, and not touch the primary resource at all.
