param name string
param tags object
param location string
param applicationGroupId string

resource workspace 'Microsoft.DesktopVirtualization/workspaces@2021-03-09-preview' = {
  name: 'ws-${name}'
  tags: tags
  location: location
  properties: {
    friendlyName: name
    description: name
    applicationGroupReferences: [
      applicationGroupId
    ]
  }
}
