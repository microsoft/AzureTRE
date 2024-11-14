param name string
param tags object
param location string
param vnetId string
param subnetName string
param localAdminName string
@secure()
param localAdminPassword string
param vmSize string
param hostPoolRegToken string

param deploymentNameStructure string = '${name}-${utcNow()}'
param intuneEnroll bool = false
param hostPoolName string
param vmCount int = 1

// All N-series except for NV_v4 use Nvidia
var installNVidiaGPUDriver = (startsWith(vmSize, 'Standard_N') && !(endsWith(vmSize, '_v4'))) ? true : false
// NV_v4 uses AMD
var installAmdGPUDriver = (startsWith(vmSize, 'Standard_NV') && endsWith(vmSize, '_v4')) ? true : false

// Use the same VM templates as used by the Add VM to hostpool Portal
var nestedTemplatesLocation = 'https://wvdportalstorageblob.blob.core.windows.net/galleryartifacts/armtemplates/Hostpool_12-9-2021/nestedTemplates/'
var vmTemplateUri = '${nestedTemplatesLocation}managedDisks-galleryvm.json'

var rdshPrefix = 'vm-${take(name, 10)}-'
var subnetId = '${vnetId}/subnets/${subnetName}'

resource availabilitySet 'Microsoft.Compute/availabilitySets@2021-11-01' = {
  name: 'avail-${name}'
  location: location
  properties: {
    platformFaultDomainCount: 2
    platformUpdateDomainCount: 5
  }
  sku: {
    name: 'Aligned'
  }
  tags: tags
}

// Deploy the session host VMs just like the Add VM to hostpool process would
resource vmDeployment 'Microsoft.Resources/deployments@2021-04-01' = {
  name: replace(deploymentNameStructure, '{rtype}', 'AVD-VMs')
  properties: {
    mode: 'Incremental'
    templateLink: {
      uri: vmTemplateUri
      contentVersion: '1.0.0.0'
    }
    parameters: {
      artifactsLocation: {
        value: 'https://wvdportalstorageblob.blob.core.windows.net/galleryartifacts/Configuration_02-23-2022.zip'
      }
      availabilityOption: {
        value: 'AvailabilitySet'
      }
      availabilitySetName: {
        value: availabilitySet.name
      }
      vmGalleryImageOffer: {
        value: 'office-365'
      }
      vmGalleryImagePublisher: {
        value: 'microsoftwindowsdesktop'
      }
      vmGalleryImageHasPlan: {
        value: false
      }
      vmGalleryImageSKU: {
        value: 'win11-21h2-avd-m365'
      }
      rdshPrefix: {
        value: rdshPrefix
      }
      rdshNumberOfInstances: {
        value: vmCount
      }
      rdshVMDiskType: {
        value: 'StandardSSD_LRS'
      }
      rdshVmSize: {
        value: vmSize
      }
      enableAcceleratedNetworking: {
        value: true
      }
      vmAdministratorAccountUsername: {
        value: localAdminName
      }
      vmAdministratorAccountPassword: {
        value: localAdminPassword
      }
      // These values are required but unused for AAD join
      administratorAccountUsername: {
        value: ''
      }
      administratorAccountPassword: {
        value: ''
      }
      // End required but unused for AAD join
      'subnet-id': {
        value: subnetId
      }
      vhds: {
        value: 'vhds/${rdshPrefix}'
      }
      location: {
        value: location
      }
      createNetworkSecurityGroup: {
        value: false
      }
      vmInitialNumber: {
        value: 0
      }
      hostpoolName: {
        value: hostPoolName
      }
      hostpoolToken: {
        value: hostPoolRegToken
      }
      aadJoin: {
        value: true
      }
      intune: {
        // In the CSE TRE DEMO tenant, Intune does not appear to be config'd
        value: intuneEnroll
      }
      securityType: {
        value: 'TrustedLaunch'
      }
      secureBoot: {
        value: true
      }
      vTPM: {
        value: true
      }
      vmImageVhdUri: {
        value: ''
      }
    }
  }
}

resource sessionHostGPUDriver 'Microsoft.Compute/virtualMachines/extensions@2020-06-01' = [for i in range(0, vmCount): if (installNVidiaGPUDriver) {
  name: '${rdshPrefix}${i}/InstallNvidiaGpuDriverWindows'
  location: location
  tags: tags
  properties: {
    publisher: 'Microsoft.HpcCompute'
    type: 'NvidiaGpuDriverWindows'
    typeHandlerVersion: '1.3'
    autoUpgradeMinorVersion: true
  }
  dependsOn: [
    vmDeployment
  ]
}]

resource sessionHostAMDGPUDriver 'Microsoft.Compute/virtualMachines/extensions@2021-11-01' = [for i in range(0, vmCount): if (installAmdGPUDriver) {
  name: '${rdshPrefix}${i}/AmdGpuDriverWindows'
  location: location
  tags: tags
  properties: {
    publisher: 'Microsoft.HpcCompute'
    type: 'AmdGpuDriverWindows'
    typeHandlerVersion: '1.0'
    autoUpgradeMinorVersion: true
  }
}]
