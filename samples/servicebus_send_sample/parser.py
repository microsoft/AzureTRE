import os
import time
from azure.cli.core import get_default_cli

def az_cli (args_str):
    args = args_str.split()
    cli = get_default_cli()
    cli.invoke(args)
    if cli.result.result:
        return cli.result.result
    elif cli.result.error:
        raise cli.result.error
    return True

aci_response = ""
        
while "Error" not in aci_response and "Success" not in aci_response:
    print("Waiting for runner to execute")
    time.sleep(5)
    aci_response = str(az_cli("container logs -n aci-cnab-0c03ba50-f671-4bf1-9312-97b5f14e42cc -g rg-msfttre-dev-9075"))
             
    print(aci_response)

if "Error" in aci_response:
    print(aci_response.split("Error",1)[1])
elif "Success" in aci_response:
    print(aci_response.split("Success",1)[1])