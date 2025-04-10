# Adding Firewall Rules as part of a workspace or service deployment

A TRE service may require certain firewall rules to be opened in the TRE firewall. Examples include:

- Access to an external authorisation endpoint
- Access to an external data store
- Access to an external API

Please be aware when opening firewall rules there is the potential for data to be leaked from the workspace to the external location.

## Firewall Rules in Template Schema

Azure TRE uses the `template_schema.json` file of the service in question (e.g. `templates/workspace_services/azureml/template_schema.json`) to define firewall rules. These rules are configured in the `pipeline` section at the end of the schema file.

### Pipeline Structure

Firewall rules are defined in steps within the pipeline sections for `install`, `upgrade`, and `uninstall` operations. Each operation contains steps that modify the firewall configuration during that operation. Please note that at the moment only the `upgrade` step is implemented, `install` and `uninstall` will be implemented in the future.

Please see [Pipeline Templates Overview](../tre-templates/pipeline-templates/overview.md) for more information on the pipeline structure.

Example pipeline step:

```json
{
  "stepId": "260421b3-7308-491f-b531-e007cdc0ff46",
  "stepTitle": "Add network firewall rules",
  "resourceTemplateName": "tre-shared-service-firewall",
  "resourceType": "shared-service",
  "resourceAction": "upgrade",
  "properties":  "properties": [
          {
            "name": "network_rule_collections",
            "type": "array",
            "arraySubstitutionAction": "replace",
            "arrayMatchField": "name",
            "value": {
              "name": "nrc_svc_{{ resource.id }}_azureml",
              "action": "Allow",
              "rules": [
                {
                  "name": "AzureMachineLearning",
                  "description": "Azure Machine Learning rules",
                  "source_addresses": "{{ resource.properties.aml_subnet_address_prefixes }}",
                  "destination_addresses": [
                    "AzureMachineLearning"
                  ],
                  "destination_ports": [
                    "443",
                    "8787",
                    "18881"
                  ],
                  "protocols": [
                    "TCP"
                  ]
                },
               // More property values defined here as needed.
              ]
            }
          },

        ]
}
```

### Rule Collection Types

There are two main types of rule collections in Azure TRE:

| Collection Type | Description |
|-----------------|-------------|
| `network_rule_collections` | Controls traffic based on source, destination, protocol, and port |
| `rule_collections` | Application-level rules controlling traffic to specific FQDNs |

#### Network Rule Collections

Network rule collections control traffic at the network level and are configured with the following properties:

| Property | Description |
|----------|-------------|
| `name` | Unique identifier for the rule collection |
| `action` | Action to take (Allow/Deny) |
| `rules` | Array of individual network rules |

Each network rule has the following structure:

| Property | Description | Example |
|----------|-------------|---------|
| `name` | Rule name | "AzureMachineLearning" |
| `description` | Human-readable description | "Azure Machine Learning rules" |
| `source_addresses` | Origin of traffic | "{{ resource.properties.aml_subnet_address_prefixes }}" |
| `destination_addresses` | Target of traffic | ["AzureMachineLearning"] |
| `destination_ports` | Allowed ports | ["443", "8787"] |
| `protocols` | Allowed protocols | ["TCP"] |

#### Application Rule Collections

Application rule collections control traffic at the application level and are configured with the following properties:

| Property | Description |
|----------|-------------|
| `name` | Unique identifier for the rule collection |
| `action` | Action to take (Allow/Deny) |
| `rules` | Array of individual application rules |

Each application rule has the following structure:

| Property | Description | Example |
|----------|-------------|---------|
| `name` | Rule name | "AzureML_client" |
| `description` | Human-readable description | "AzureML rules" |
| `source_addresses` | Origin of traffic | "{{ resource.properties.workspace_address_spaces }}" |
| `target_fqdns` | Target FQDNs | ["aadcdn.msauth.net"] |
| `protocols` | Protocol configuration | [{"port": "443", "type": "Https"}] |

### Rule Collection Operations

When modifying rule collections, you can specify how the rules should be applied:

| Operation | Description |
|-----------|-------------|
| `replace` | Replace existing rules that match the specified criteria, typically used in `install` and `upgrade` steps |
| `remove` | Remove rules that match the specified criteria, typically used in `uninstall` steps |

This is controlled by the `arraySubstitutionAction` property:

```json
{
  "name": "network_rule_collections",
  "type": "array",
  "arraySubstitutionAction": "replace",
  "arrayMatchField": "name",
  "value": {
              "name": "nrc_svc_{{ resource.id }}_azureml",
              "action": "Allow",
              "rules": [
                {
                  "name": "AzureMachineLearning",
                  "description": "Azure Machine Learning rules",
                  "source_addresses": "{{ resource.properties.aml_subnet_address_prefixes }}",
                  "destination_addresses": [
                    "AzureMachineLearning"
                  ],
                  "destination_ports": [
                    "443",
                    "8787",
                    "18881"
                  ],
                  "protocols": [
                    "TCP"
                  ]
                },
               // More property values defined here as needed.
              ]
            }
}
```

### Template Variables

Firewall rules often use template variables to dynamically set values:

| Variable Pattern | Description | Example |
|------------------|-------------|---------|
| `{{ resource.id }}` | The resource ID | Used in rule collection names |
| `{{ resource.properties.x }}` | Resource-specific properties | Address spaces, FQDNs |

### Example Rule Collection

Below is an example of a network rule collection for Azure Machine Learning:

```json
{
  "name": "nrc_svc_{{ resource.id }}_azureml",
  "action": "Allow",
  "rules": [
    {
      "name": "AzureMachineLearning",
      "description": "Azure Machine Learning rules",
      "source_addresses": "{{ resource.properties.aml_subnet_address_prefixes }}",
      "destination_addresses": ["AzureMachineLearning"],
      "destination_ports": ["443", "8787", "18881"],
      "protocols": ["TCP"]
    }
  ]
}
```

## Best Practices

1. **Use descriptive names and descriptions** for rule collections and individual rules.
2. **Minimize the scope** of firewall rules to only what is necessary.
3. **Document any custom rules** in your service documentation.
4. **Test thoroughly** after making changes to firewall rules.
5. **Review rules periodically** to ensure they are still required.

