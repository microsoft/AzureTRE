# Download Git For Windows
# We use useBasicParsing to skip Internet Explorer's first launch configuration
$GitVersion ="Git-2.35.1.2-64-bit"
Invoke-WebRequest -UseBasicParsing "https://github.com/git-for-windows/git/releases/download/v2.35.1.windows.2/$GitVersion.exe" -OutFile "$env:windir/Temp/$GitVersion.exe"

# Install Git
&"$env:windir/temp/$GitVersion.exe" /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /COMPONENTS="icons,ext\reg\shellhere,assoc,assoc_sh"

# Download Azure Cli
Invoke-WebRequest -UseBasicParsing https://aka.ms/installazurecliwindows -OutFile $env:windir/temp/AzureCli.msi

# Install Azure Cli
Msiexec.exe /i "$env:windir\Temp\AzureCli.msi" /qn /L*v "$env:windir\Temp\AzureCLI-Install.log"

# Download JQ
Invoke-WebRequest -UseBasicParsing https://github.com/stedolan/jq/releases/latest/download/jq-win64.exe -OutFile "$env:ProgramFiles\Git\usr\bin\jq.exe"

# Clone TRE repository on C:/AzureTRE
cd $env:systemdrive/
$installed = $false;
for ($i = 0; $i -lt 6; $i++){
	if ((test-path "$env:ProgramFiles\Git\usr\bin\mintty.exe")){
		&"C:\Program Files\Git\usr\bin\mintty.exe" --exec "/bin/bash" --login -c "/cmd/git clone https://github.com/microsoft/AzureTRE.git"
        $installed = $true;
		break;
	}
    else{
        sleep(10);
    }
}

if(!$installed){"Something went wrong with GIT installation" >> post_install.log}
