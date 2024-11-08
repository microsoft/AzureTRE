# Start/Stop Azure TRE

Once you've provisioned an Azure TRE instance it will begin to incur running costs of the underlying Azure services.

Within evaluation or development, you may want to "pause" the TRE environment during out of office hours or weekends, to reduce costs without having to completely destroy the environment.  The following `make` targets provide a simple way to start and stop both the Azure Firewall and Azure Application Gateway instances, considerably reducing the Azure TRE instance running costs.

!!! info
    After running `make all` underlying Azure TRE services are automatically started and billing will start.

## Start Azure TRE

This will allocate the Azure Firewall settings with a public IP and start the Azure Application Gateway service, starting billing of both services.

```bash
make tre-start
```

## Stop Azure TRE

This will deallocate the Azure Firewall public IP and stop the Azure Application Gateway service, stopping billing of both services.

```bash
make tre-stop
```

## Automating `stop`

In certain situations, you might want to stop any TRE running on a schedule to reduce costs in a wider way.
We have this procedure setup in our development subscriptions where each night we stop all our environments after which each developer would need to _manually_ start their TRE when they need it again.

### Requirements

We use [Azure Automation](https://learn.microsoft.com/azure/automation/overview) to run this procedure.

Be sure to create a runbook with PowerShell 7.1 or PowerShell 7.2 enabled and an identity with contributor permissions on the subscription. Note that the script below uses a system managed identity and if you use something different then you might need to update the authentication part.

If you create a new Automation account, you will have the required modules preinstalled.

Finally, schedule it to run when it makes sense for you.

### Stop Runbook Script

```powershell
try {
  "Logging in to Azure..."
  Connect-AzAccount -Identity
}
catch {
  Write-Error -Message $_.Exception
  throw $_.Exception
}

$azContext = Get-AzContext
$azProfile = [Microsoft.Azure.Commands.Common.Authentication.Abstractions.AzureRmProfileProvider]::Instance.Profile
$profileClient = New-Object -TypeName Microsoft.Azure.Commands.ResourceManager.Common.RMProfileClient -ArgumentList ($azProfile)
$token = $profileClient.AcquireAccessToken($azContext.Subscription.TenantId)

$authHeader = @{
  'Content-Type'  = 'application/json'
  'Authorization' = 'Bearer ' + $token.AccessToken
}

# Get all resource groups that have the default Azure TRE project tag value
$ResourceGroups = Get-AzResourceGroup -Tag @{'project' = 'Azure Trusted Research Environment' }
foreach ($Group in $ResourceGroups) {
  if ($Group.ResourceGroupName -like '*-ws-*') {
    # Deal with the workspace resource groups separately (below)
    continue
  }

  # Deallocate the Azure Firewall (expecting only one per TRE instance)
  $Firewall = Get-AzFirewall -ResourceGroupName $Group.ResourceGroupName
  if ($null -ne $Firewall) {
    $Firewall.Deallocate()
    Write-Output "Deallocating Firewall '$($Firewall.Name)'"
    Set-AzFirewall -AzureFirewall $Firewall
  }

  # Stop the Application Gateway(s)
  # Multiple Application Gateways may exist if the certs shared service is installed
  $Gateways = Get-AzApplicationGateway -ResourceGroupName $Group.ResourceGroupName
  foreach ($Gateway in $Gateways) {
    Write-Output "Stopping Application Gateway '$($Gateway.Name)'"
    Stop-AzApplicationGateway -ApplicationGateway $Gateway
  }

  # Stop the MySQL servers
  $MySQLServers = Get-AzResource -ResourceGroupName $Group.ResourceGroupName -ResourceType "Microsoft.DBforMySQL/servers"
  foreach ($Server in $MySQLServers) {
    # Invoke the REST API
    Write-Output "Stopping MySQL '$($Server.Name)'"
    $restUri = 'https://management.azure.com/subscriptions/' + $azContext.Subscription.Id + '/resourceGroups/' + $Group.ResourceGroupName + '/providers/Microsoft.DBForMySQL/servers/' + $Server.Name + '/stop?api-version=2020-01-01'
    $response = Invoke-RestMethod -Uri $restUri -Method POST -Headers $authHeader
  }

  # Deallocate all the virtual machine scale sets (resource processor)
  $VMSS = Get-AzVMSS -ResourceGroupName $Group.ResourceGroupName
  foreach ($item in $VMSS) {
    Write-Output "Stopping VMSS '$($item.Name)'"
    Stop-AzVmss -ResourceGroupName $item.ResourceGroupName -VMScaleSetName $item.Name -Force
  }

  # Deallocate all the VMs
  $VM = Get-AzVM -ResourceGroupName $Group.ResourceGroupName
  foreach ($item in $VM) {
    Write-Output "Stopping VM '$($item.Name)'"
    Stop-AzVm -ResourceGroupName $item.ResourceGroupName -Name $item.Name -Force
  }

  # Process all the workspace resource groups for this TRE instance
  $WorkspaceResourceGroups = Get-AzResourceGroup -Name "$($Group.ResourceGroupName)-ws-*"
  foreach ($wsrg in $WorkspaceResourceGroups) {
    # Deallocate all the VMs
    $VM = Get-AzVM -ResourceGroupName $wsrg.ResourceGroupName
    foreach ($item in $VM) {
      Write-Output "Stopping workspace VM '$($item.Name)'"
      Stop-AzVm -ResourceGroupName $item.ResourceGroupName -Name $item.Name -Force
    }
  }
}
```

### Automating `start`

To restart the TRE core services (Firewall, Application Gateway(s), Virtual Machine Scale Sets, Virtual Machines, and MySQL), you can use `make tre-start`. Depending on your workflow, you might not be able to easily execute the `make` target. Alternatively, you can create a second Runbook and execute it manually. The PowerShell code to start TRE core services is below:

```powershell
try {
    "Logging in to Azure..."
    Connect-AzAccount -Identity
}
catch {
    Write-Error -Message $_.Exception
    throw $_.Exception
}

$azContext = Get-AzContext
$azProfile = [Microsoft.Azure.Commands.Common.Authentication.Abstractions.AzureRmProfileProvider]::Instance.Profile
$profileClient = New-Object -TypeName Microsoft.Azure.Commands.ResourceManager.Common.RMProfileClient -ArgumentList ($azProfile)
$token = $profileClient.AcquireAccessToken($azContext.Subscription.TenantId)

$authHeader = @{
    'Content-Type'  = 'application/json'
    'Authorization' = 'Bearer ' + $token.AccessToken
}

# Get all resource groups that have the default Azure TRE project tag value
$ResourceGroups = Get-AzResourceGroup -Tag @{'project' = 'Azure Trusted Research Environment' }
foreach ($Group in $ResourceGroups) {
    if ($Group.ResourceGroupName -like '*-ws-*') {
        # Don't deal with the workspace resource groups
        continue
    }

    $azureTreId = $Group.Tags['tre_id']
    Write-Output "Starting TRE core resources for '$azureTreId'"

    # Allocate the Azure Firewall (expecting only one per TRE instance)
    $Firewall = Get-AzFirewall -ResourceGroupName $Group.ResourceGroupName
    if ($null -ne $Firewall) {
        # Find the firewall's public IP and virtual network
        $pip = Get-AzPublicIpAddress -ResourceGroupName $Group.ResourceGroupName -Name "pip-fw-$azureTreId"
        $vnet = Get-AzVirtualNetwork -ResourceGroupName $Group.ResourceGroupName -Name "vnet-$azureTreId"
        # Find the firewall's public management IP - note this will only be present for a firewall with a Basic SKU
        $mgmtPip = Get-AzPublicIpAddress -ResourceGroupName "rg-$azureTreId" -Name "pip-fw-management-$azureTreId" -ErrorAction SilentlyContinue
        $Firewall.Allocate($vnet, $pip, $mgmtPip)
        Write-Output "Allocating Firewall '$($Firewall.Name)' with public IP '$($pip.Name)'"
        Set-AzFirewall -AzureFirewall $Firewall
    }

    # Start the Application Gateway(s)
    # Multiple Application Gateways may exist if the certs shared service is installed
    $Gateways = Get-AzApplicationGateway -ResourceGroupName $Group.ResourceGroupName
    foreach ($Gateway in $Gateways) {
        Write-Output "Starting Application Gateway '$($Gateway.Name)'"
        Start-AzApplicationGateway -ApplicationGateway $Gateway
    }

    # Start the MySQL servers
    $MySQLServers = Get-AzResource -ResourceGroupName $Group.ResourceGroupName -ResourceType "Microsoft.DBforMySQL/servers"
    foreach ($Server in $MySQLServers) {
        # Invoke the REST API
        Write-Output "Starting MySQL '$($Server.Name)'"
        $restUri = 'https://management.azure.com/subscriptions/' + $azContext.Subscription.Id + '/resourceGroups/' + $Group.ResourceGroupName + '/providers/Microsoft.DBForMySQL/servers/' + $Server.Name + '/start?api-version=2020-01-01'
        $response = Invoke-RestMethod -Uri $restUri -Method POST -Headers $authHeader
    }

    # Allocate all the virtual machine scale sets (resource processor)
    $VMSS = Get-AzVMSS -ResourceGroupName $Group.ResourceGroupName
    foreach ($item in $VMSS) {
        Write-Output "Starting VMSS '$($item.Name)'"
        Start-AzVmss -ResourceGroupName $item.ResourceGroupName -VMScaleSetName $item.Name
    }

    # Start VMs
    $VM = Get-AzVM -ResourceGroupName $Group.ResourceGroupName
    foreach ($item in $VM) {
      Write-Output "Starting VM '$($item.Name)'"
      Start-AzVm -ResourceGroupName $item.ResourceGroupName -Name $item.Name
    }
}
```
