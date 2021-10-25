param (
  [Parameter(Mandatory = $True, HelpMessage = "The action to carry out - Start or Stop")]
  [ValidateSet("Start", "Stop")]
  [String] $Action
)

. ./devops/scripts/Set-Env.ps1 ./devops/.env
. ./devops/scripts/Set-Env.ps1 ./templates/core/.env

Set-AzContext -SubscriptionId $env:ARM_SUBSCRIPTION_ID -ErrorAction Continue
foreach ($eacherror in $Error) {
  if ($eacherror.ToString() -like "*Run Connect-AzAccount to login.*" -or $eacherror.ToString() -like "*Please provide a valid tenant or a valid subscription.") {
    Write-Host "Login failed. Please check your credentials and try again."
    Connect-AzAccount -UseDeviceAuthentication
    Set-AzContext -SubscriptionId $env:ARM_SUBSCRIPTION_ID
  }
}

# Deactivate Firwall
Write-Host "$($Action) Firewall..."
$firewall = Get-AzFirewall -ResourceGroupName "rg-$env:TRE_ID" -Name "fw-$env:TRE_ID"

if ($Action -eq "Start") {
  $vnet = Get-AzVirtualNetwork -ResourceGroupName "rg-$env:TRE_ID" -Name "vnet-$env:TRE_ID"
  $publicip1 = Get-AzPublicIpAddress -Name  "pip-fw-$env:TRE_ID" -ResourceGroupName "rg-$env:TRE_ID"
  $firewall.Allocate($vnet, $publicip1) | out-null
}
elseif ($Action -eq "Stop") {
  $firewall.Deallocate() | out-null
}
$firewall | Set-AzFirewall | out-null

# Deactivate Application Gateway
Write-Host "$($Action) Application Gateway..."
$appgw = Get-AzApplicationGateway -ResourceGroupName "rg-$env:TRE_ID" -Name "agw-$env:TRE_ID"
if ($Action -eq "Start") {
  Start-AzApplicationGateway -ApplicationGateway $appgw | out-null
}
elseif ($Action -eq "Stop") {
  Stop-AzApplicationGateway -ApplicationGateway $appgw | out-null
}

# Write out status
if ($firewall.ipConfigurations.Count -gt 0) {
  Write-Host "Firewall: Running"
}
else {
  Write-Host "Firewall: Stopped"
}

Write-Host "Application Gateway:" $appgw.OperationalState
