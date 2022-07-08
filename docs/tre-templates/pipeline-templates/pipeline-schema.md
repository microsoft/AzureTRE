# Pipeline Template Schema
This document will help you write a valid `pipeline: {}` block in your template.

> For a working example, see `./templates/shared-services/sonatype-nexus/template_schema.json`.

## Schema
```json
"pipeline": {
    "install": [ // <-- [install | upgrade | uninstall]
      {
        "stepId": "a unique string value here",
        "stepTitle": "Friendly description of the step here - will be displayed in the UI",
        "resourceTemplateName": "name of the resource template to update", // only required for shared_service targets
        "resourceType": "shared_service", // [ shared_service | user_resource | workspace_service | workspace ]
        "resourceAction": "upgrade", // <-- currently only upgrade supported
        "properties": [
        {
          "name": "display_name",
          "type": "string",
          "value": "A new name here!"
        }]
      },
      {
        "stepId": "main" // <-- deployment of the VM resource
      },

```

## Substituting Resource Property Values
It's possible to refer to properties from the primary resource (the resource that triggered this pipeline) in the template steps. The values will be substituted in at runtime.

The syntax is `{{ resource.propertyName }}`. For example: `"{{ resource.properties.display_name }}"`.

Example pipeline in `template_schema.json`:
The below example references 2 properties from the primary resource to be used in updating the firewall shared service.

```json
"pipeline": {
    "upgrade": [
      {
        "stepId": "1234567-87654-2345-6543",
        "stepTitle": "Update a firewall rule",
        "resourceTemplateName": "tre-shared-service-firewall",
        "resourceType": "shared_service", 
        "resourceAction": "upgrade",
        "arraySubstitutionAction": "replace", // <-- [append | remove | replace]
        "arrayMatchField": "name", // <-- name of the field in the array object to match on, for remove / replace
        "properties": [
        {
          "name": "rule_collections",
          "type": "array", // <-- More on array types below
          "value": { // <-- value can be string or object
              "name": "my-firewall-rule-collection",
              "action": "Allow",
              "rules": [
                {
                  "name": "my-rules",
                  "target_fqdns": "{{ resource.properties.fqdns_list }}",
                  "source_addresses": "{{ resource.properties.address_prefixes }}"
                }
          }
        }]
      },
```

## Working with Properties Containing Arrays
It's possible that a resource property would actually be an array. As an example, the firewall shared service has the `rule_collections` property. This single property contains
an array of objects. Since the values inside this array may have been sourced from different resources, it's important to leave other values in tact when modifying the property.
To do so, the `arraySubstitutionAction` field supports the following values:
- `append` - just append this object into the array
- `replace` - find this object in the array (using the `arrayMatchField` value), and replace it with this value
- `remove` - remove this property from the array (useful for `uninstall` actions)

## Notes
- Each step is executed in serial, in the order defined in the template
- Theoretically any number of steps could be created
- A step with `step_id` of `main` represents where in the chain the primary resource will get deployed. It is possible to omit this step altogether, and not touch the primary resource at all.
