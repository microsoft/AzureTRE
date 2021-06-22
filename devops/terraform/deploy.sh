terraform init -input=false -backend=true -reconfigure -upgrade
terraform plan
terraform apply -auto-approve