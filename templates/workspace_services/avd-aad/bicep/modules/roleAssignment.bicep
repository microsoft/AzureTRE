param name string

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2020-10-01-preview' = {
  name: 'rbac${name}'
  properties: {
    roleDefinitionId: 'string'
    principalId: 'string'
    principalType: 'string'
    description: 'string'
    condition: 'string'
    conditionVersion: 'string'
    delegatedManagedIdentityResourceId: 'string'
  }
}
