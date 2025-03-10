# Configuring DNS Security in Azure TRE

This document provides steps to configure DNS security in Azure Trusted Research Environment (TRE) to block unauthorized DNS queries and prevent DNS tunneling.

## Prerequisites

Before configuring DNS security, ensure that you have the following prerequisites:
- Access to the Azure portal with sufficient permissions to manage DNS settings.
- An existing Azure TRE deployment.

## Steps to Configure DNS Security

### Step 1: Add DNS Security Policy

1. Open the `core/terraform/airlock/airlock_processor.tf` file.
2. Add the following configuration to create a DNS security policy:

```hcl
resource "azurerm_dns_resolver_policy" "dns_security_policy" {
  name                = "dns-security-policy-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  dns_resolver_id     = azurerm_dns_resolver.dns_resolver.id
  policy_type         = "Security"
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_dns_resolver_policy_rule" "dns_security_rule" {
  name                = "dns-security-rule-${var.tre_id}"
  resource_group_name = var.resource_group_name
  dns_resolver_policy_id = azurerm_dns_resolver_policy.dns_security_policy.id
  action              = "Deny"
  domain_name         = "*"
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}
```

### Step 2: Configure Azure DNS Private Resolver

1. Open the `core/terraform/network/dns_zones.tf` file.
2. Add the following configuration to create an Azure DNS Private Resolver:

```hcl
resource "azurerm_dns_resolver" "dns_resolver" {
  name                = "dns-resolver-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  inbound_endpoint {
    name      = "inbound-endpoint"
    subnet_id = var.airlock_processor_subnet_id
  }

  outbound_endpoint {
    name      = "outbound-endpoint"
    subnet_id = var.airlock_processor_subnet_id
  }
}

resource "azurerm_dns_resolver_rule" "dns_resolver_rule" {
  name                = "dns-resolver-rule-${var.tre_id}"
  resource_group_name = var.resource_group_name
  dns_resolver_id     = azurerm_dns_resolver.dns_resolver.id
  domain_name         = "*"
  rule_type           = "Forward"
  target_dns_servers {
    ip_address = "0.0.0.0"
  }
  tags = var.tre_core_tags

  lifecycle { ignore changes = [tags] }
}
```

### Step 3: Update Outputs

1. Open the `core/terraform/network/outputs.tf` file.
2. Add the following output for the DNS resolver configuration:

```hcl
output "dns_resolver_id" {
  value = azurerm_dns_resolver.dns_resolver.id
}
```

## Verification

After applying the changes, verify that the DNS security policy and resolver are correctly configured by checking the Azure portal. Ensure that unauthorized DNS queries are blocked and DNS tunneling is prevented.

For further assistance, refer to the Azure documentation or contact your Azure support representative.
