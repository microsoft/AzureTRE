# Extend the C:\ drive to the end of the disk
Write-Output "*** Extending C:\ drive to fill the disk"
$size = Get-PartitionSupportedSize -DriveLetter C
Resize-Partition -DriveLetter C -Size $size.SizeMax

# Download the review data
Write-Output "*** Downloading review data"
$DownloadPath = $env:Public + "\Desktop\ReviewData"
mkdir $DownloadPath
az storage blob download-batch -d $DownloadPath -s '"${airlock_request_sas_url}"'
