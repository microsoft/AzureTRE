terraform init -input=false -backend=true -reconfigure
terraform plan
terraform apply -auto-approve