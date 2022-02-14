param ($storageAccountName, $fileShareName, $storageAccountKeys)
$password = ConvertTo-SecureString -String $storageAccountKeys -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential -ArgumentList "AZURE\$($storageAccountName)", $password
New-PSDrive -Name Z -PSProvider FileSystem -Root "\\$($storageAccountName).file.core.windows.net\$($fileShareName)" -Credential $credential -Persist
