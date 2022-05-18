param name string
param tags object
param location string
@allowed([
  'Personal'
  'Pooled'
])
param hostPoolType string

param baseTime string = utcNow('u')

var expirationTime = dateTimeAdd(baseTime, 'PT48H')

resource hostPool 'Microsoft.DesktopVirtualization/hostPools@2021-03-09-preview' = {
  name: 'hp-${name}'
  location: location
  tags: tags
  properties: {
    hostPoolType: hostPoolType
    loadBalancerType: 'BreadthFirst'
    preferredAppGroupType: 'Desktop'
    maxSessionLimit: 999999
    startVMOnConnect: false
    validationEnvironment: false
    customRdpProperty: 'drivestoredirect:s:*;audiomode:i:0;videoplaybackmode:i:1;redirectclipboard:i:1;redirectprinters:i:1;devicestoredirect:s:*;redirectcomports:i:1;redirectsmartcards:i:1;usbdevicestoredirect:s:*;enablecredsspsupport:i:1;use multimon:i:1;targetisaadjoined:i:1'
    registrationInfo: {
      expirationTime: expirationTime
      token: null
      registrationTokenOperation: 'Update'
    }
  }
}

output id string = hostPool.id
output name string = hostPool.name
output token string = string(hostPool.properties.registrationInfo.token)
