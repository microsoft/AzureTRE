# Configuring Firewall Rules in Azure TRE

This guide explains how to configure firewall rules for your Azure TRE environment.

## Contents
- [Overview](#overview)
- [Types of Firewall Rules](#types-of-firewall-rules)
- [Configuring Application Rules](#configuring-application-rules)
- [Configuring Network Rules](#configuring-network-rules)
- [Applying Your Configuration](#applying-your-configuration)
- [Examples](#examples)

## Overview

The Azure TRE Firewall shared service controls network traffic flowing in and out of your research environment. The firewall configuration is defined using a JSON file that specifies rule collections and their associated rules.

## Types of Firewall Rules

The Azure TRE Firewall supports two types of rules:

1. **Application Rules**: Control outbound access to specific websites/FQDNs
2. **Network Rules**: Control traffic based on source, destination, port, and protocol

## Configuring Application Rules

Application rules control HTTP/HTTPS traffic to specific web destinations.

To configure application rules:

1. Create a JSON file containing a `rule_collections` array
2. Define one or more rule collections, each with a unique name
3. Within each collection, define individual rules

### Application Rule Structure

```json
{
  "rule_collections": [
    {
      "name": "my-app-rule-collection",
      "rules": [
        {
          "name": "allow-microsoft-services",
          "description": "Allow access to Microsoft services",
          "protocols": [
            {
              "port": "443",
              "type": "Https"
            }
          ],
          "target_fqdns": [
            "*.microsoft.com",
            "*.windowsazure.com"
          ],
          "source_addresses": [
            "10.1.0.0/22"
          ]
        }
      ]
    }
  ]
}
```

## Application Rule Properties

| Property | Description | Required | Example|
|----------|-------------|----------|--------|
|`name` | Name of the rule | Yes | `"allow-github"`|
|`description` | Description of the rule | No | `"Allow access to GitHub"`|
|`protocols` | Array of protocol objects | Yes | See below|
|`target_fqdns` | Array of destination FQDNs | No |`["github.com", "*.github.io"]`|
|`fqdn_tags` | Array of predefined FQDN tags | No |`["AzureKubernetesService"]`|
|`source_addresses` | Array of source IP addresses/ranges | No | `["10.1.0.0/22"]`|
|`source_ip_group_ids` | Array of source IP group resource IDs | No | `["/subscriptions/.../ipGroups/myIpGroup"]`|
|`source_ip_groups_in_core` | Array of IP group names in the core resource group | No | `["core_ip_group"]`|

Each protocol object requires:

`port`: The port number (e.g., `"443"`)
`type`: One of: `"Http"`, `"Https"`, or `"Mssql"`

## Configuring Network Rules
Network rules control traffic based on IP addresses, ports, and protocols.

To configure network rules:

1. Create a JSON file containing a `network_rule_collections` array
2. Define one or more rule collections, each with a unique name
3. Within each collection, define individual rules

## Network Rule Structure
 ```json
 {
  "network_rule_collections": [
    {
      "name": "my-network-rule-collection",
      "rules": [
        {
          "name": "allow-rdp-access",
          "source_addresses": [
            "10.1.0.0/22"
          ],
          "destination_addresses": [
            "10.2.0.0/24"
          ],
          "destination_ports": [
            "3389"
          ],
          "protocols": [
            "TCP"
          ]
        }
      ]
    }
  ]
}
```
## Network Rule Properties

|Property |Description |Required |Example |
|---------|------------|---------|--------|
|`name` |Name of the rule (5-80 characters) |Yes |`"allow-ssh-access"` |
|`description` |Description of the rule (Deprecated) |No |`"Allow SSH access to VMs"` |
|`source_addresses` |Array of source IP addresses/ranges |No |`["10.1.0.0/22"]` |
|`source_ip_group_ids` |Array of source IP group resource IDs |No |`["/subscriptions/.../ipGroups/myIpGroup"]` |
|`source_ip_groups_in_core`| Array of IP group names in the core resource group |No |`["core_ip_group"]` |
|`destination_addresses`| Array of destination IP addresses/ranges |No |`["10.2.0.0/24"]` |
|`destination_ip_group_ids`| Array of destination IP group resource IDs |No |`["/subscriptions/.../ipGroups/destIpGroup"]` |
|`destination_fqdns`| Array of destination FQDNs |No |`["example.com"]` |
|`destination_ports`| Array of destination ports |No |`["22", "443", "1000-2000"]` |
|`protocols`| Array of protocols |No |`["TCP", "UDP"]`|

Valid protocols: `"Any"`, `"ICMP"`, `"TCP"`, `"UDP"`

## Applying Your Configuration
To apply your firewall configuration:

1. Save your JSON file with your rule definitions
2. Use the Azure TRE API or UI to update the firewall shared service with your configuration

## Examples

## Example 1: Allow access to Azure services
```json
{
  "rule_collections": [
    {
      "name": "allow-azure-services",
      "rules": [
        {
          "name": "azure-public-services",
          "protocols": [
            {
              "port": "443",
              "type": "Https"
            }
          ],
          "fqdn_tags": [
            "AzureBackup",
            "WindowsUpdate"
          ],
          "source_addresses": [
            "10.1.0.0/22"
          ]
        }
      ]
    }
  ]
}
```

## Example 2: Allow outbound internet access

```json
{
  "network_rule_collections": [
    {
      "name": "outbound-internet",
      "rules": [
        {
          "name": "allow-https-outbound",
          "source_addresses": [
            "10.1.0.0/22"
          ],
          "destination_addresses": [
            "*"
          ],
          "destination_ports": [
            "443"
          ],
          "protocols": [
            "TCP"
          ]
        }
      ]
    }
  ]
}
```

## Example 3: Combined Application and Network Rules

```json
{
  "network_rule_collections": [
    {
      "name": "outbound-internet",
      "rules": [
        {
          "name": "allow-https-outbound",
          "source_addresses": [
            "10.1.0.0/22"
          ],
          "destination_addresses": [
            "*"
          ],
          "destination_ports": [
            "443"
          ],
          "protocols": [
            "TCP"
          ]
        }
      ]
    }
  ]
}
```

This configuration allows for both application-level access to Python package repositories and network-level SSH communication between specific subnets.
