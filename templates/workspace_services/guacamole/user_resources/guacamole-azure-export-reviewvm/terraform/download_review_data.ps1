mkdir "C:\Users\${username}\Desktop\REVIEW_FILES"
az storage blob download-batch -d "C:\Users\${username}\Desktop\REVIEW_FILES" -s '"${airlock_request_sas_url}"'
