# Start/Stop Azure TRE

Once you've provisioned an Azure TRE instance it will begin to incurr running costs of the underlying Azure services.

Within evaluation or development, you may want to "pause" the TRE environment during out of hours or weekends, to reduce costs without having to completely destroy the environment.  The following `make targets` provide a simple way to start and stop both the Azure Firewall and Azure Application Gateway instances, considerably reducing the Azure TRE instance running costs.

!!! info
    After running `make all` underlying Azure TRE services are automatically started, billing will start.

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

We use [Azure Automation](https://docs.microsoft.com/en-us/azure/automation/overview) to run this procedure.

Be sure to create a runbook with Powershell 7.1 enabled and an identity with contributor permissions on the subscription. Note that the script below uses a system managed identity and if you use something different then you might need to update the authentication part.

If you create a new Automation account, you will have the required modules preinstalled.

Finally, schedule it to run when it makes sense for you.

### Runbook Script

```powershell
try
{
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
    'Content-Type'='application/json'
    'Authorization'='Bearer ' + $token.AccessToken
}


$ResourceGroups = Get-AzResourceGroup -Tag @{'project'='Azure Trusted Research Environment'}
foreach ($Group in $ResourceGroups) 
{
    if ($Group.ResourceGroupName -like '*-ws-*') {
      # we deal with the workspace resource groups separately.
      continue
    }

    $Firewall = Get-AzFirewall -ResourceGroupName $Group.ResourceGroupName
    if ($Firewall -ne $null) {
        $Firewall.Deallocate()
        Write-Output "Deallocating $($Firewall.Name)"
        Set-AzFirewall -AzureFirewall $Firewall
    }

    $Gateway = Get-AzApplicationGateway -ResourceGroupName $Group.ResourceGroupName
    if ($Gateway -ne $null) {
        Write-Output "Stopping $($Gateway.Name)"
        Stop-AzApplicationGateway -ApplicationGateway $Gateway
    }

  $MySQLServers = Get-AzResource -ResourceGroupName $Group.ResourceGroupName -ResourceType "Microsoft.DBforMySQL/servers"
  foreach ($Server in $MySQLServers)
  {
    # Invoke the REST API
    Write-Output "Stopping $($Server.Name)"
    $restUri='https://management.azure.com/subscriptions/'+$azContext.Subscription.Id+'/resourceGroups/'+$Group.ResourceGroupName+'/providers/Microsoft.DBForMySQL/servers/'+$Server.Name+'/stop?api-version=2020-01-01'
    $response = Invoke-RestMethod -Uri $restUri -Method POST -Headers $authHeader
  }

  $VMSS = Get-AzVMSS -ResourceGroupName $Group.ResourceGroupName
  foreach ($item in $VMSS)
  {
    Write-Output "Stopping $($item.Name)"
    Stop-AzVmss -ResourceGroupName $item.ResourceGroupName -VMScaleSetName $item.Name -Force
  }

  $VM = Get-AzVM -ResourceGroupName $Group.ResourceGroupName
  foreach ($item in $VM)
  {
    Write-Output "Stopping $($item.Name)"
    Stop-AzVm -ResourceGroupName $item.ResourceGroupName -Name $item.Name -Force
  }

  $WorkspaceResourceGroups = Get-AzResourceGroup -Name "$($Group.ResourceGroupName)-ws-*"
  foreach ($wsrg in $WorkspaceResourceGroups)
  {
    $VM = Get-AzVM -ResourceGroupName $wsrg.ResourceGroupName
    foreach ($item in $VM)
    {
      Write-Output "Stopping $($item.Name)"
      Stop-AzVm -ResourceGroupName $item.ResourceGroupName -Name $item.Name -Force
    }
  }
}
```
