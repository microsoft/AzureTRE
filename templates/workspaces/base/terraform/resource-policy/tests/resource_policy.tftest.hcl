mock_provider "azurerm" {}

variables {
  resource_group_id = "/subscriptions/00000000-0000-0000-0000-000000000002/resourceGroups/rg-workspace"
}

run "disabled_by_default" {
  command = apply
  assert {
    condition     = length(azurerm_resource_group_policy_assignment.blocked_resource_types) == 0
    error_message = "An empty list must create no assignment."
  }
}

run "enable_bing_block" {
  command = apply
  variables {
    blocked_resource_types = ["Microsoft.Bing/accounts"]
  }
  assert {
    condition = (
      length(azurerm_resource_group_policy_assignment.blocked_resource_types) == 1
      && azurerm_resource_group_policy_assignment.blocked_resource_types[0].resource_group_id == var.resource_group_id
      && azurerm_resource_group_policy_assignment.blocked_resource_types[0].enforce
      && azurerm_resource_group_policy_assignment.blocked_resource_types[0].policy_definition_id == "/providers/Microsoft.Authorization/policyDefinitions/6c112d4e-5bc7-47ae-a041-ea2d9dccd749"
      && jsondecode(azurerm_resource_group_policy_assignment.blocked_resource_types[0].parameters).effect.value == "Deny"
      && jsondecode(azurerm_resource_group_policy_assignment.blocked_resource_types[0].parameters).listOfResourceTypesNotAllowed.value == ["Microsoft.Bing/accounts"]
    )
    error_message = "The policy must deny Bing account creation and updates only in the selected workspace."
  }
}

run "change_blocked_types" {
  command = apply
  variables {
    blocked_resource_types = ["Microsoft.Search/searchServices", "Microsoft.Bing/accounts"]
  }
  assert {
    condition = jsondecode(azurerm_resource_group_policy_assignment.blocked_resource_types[0].parameters).listOfResourceTypesNotAllowed.value == [
      "Microsoft.Bing/accounts", "Microsoft.Search/searchServices"
    ]
    error_message = "The operator must be able to select and update multiple resource types."
  }
}

run "remove_assignment" {
  command = apply
  variables {
    blocked_resource_types = []
  }
  assert {
    condition     = length(azurerm_resource_group_policy_assignment.blocked_resource_types) == 0
    error_message = "Clearing the list must remove this workspace's assignment."
  }
}

run "reject_wildcards" {
  command = plan
  variables {
    blocked_resource_types = ["Microsoft.Bing/*"]
  }
  expect_failures = [var.blocked_resource_types]
}

run "reject_resource_ids" {
  command = plan
  variables {
    blocked_resource_types = ["/subscriptions/00000000-0000-0000-0000-000000000002/resourceGroups/rg-workspace"]
  }
  expect_failures = [var.blocked_resource_types]
}

run "reject_blank_types" {
  command = plan
  variables {
    blocked_resource_types = [""]
  }
  expect_failures = [var.blocked_resource_types]
}
