$DownloadPath = $env:Public + "\Desktop\ReviewData"
mkdir $DownloadPath
az storage blob download-batch -d $DownloadPath -s '"${airlock_request_sas_url}"'
