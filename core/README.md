# Core Applications

## TRE API

### Endpoints

#### /ping

- Check if API is alive

### Run locally

Install the requirements on the dev machine

```cmd
virtualenv venv
source venv/bin/activate    # linux
venv/Scripts/activate       # windows
pip install -r core/api/requirements.txt
```

Run the webserver locally

```cmd
cd core
uvicorn api.main:app
```

This will start the API on [http://127.0.0.1:8000](http://127.0.0.1:8000) and you can interact with the swagger on [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Run the API Tests locally

```cmd
pytest
```

### Build and run in docker

From the root of the repository, build the container image:

```cmd
cd core
docker build -t tre-management-api .
```

To run:
```cmd
docker run -it -p 8000:8000 tre-management-api
```

This will start the API on [http://127.0.0.1:8000](http://127.0.0.1:8000) and you can interact with the swagger on [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Deploy manually to Azure App Service

- Install [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- Login to Azure with your credentials `az login`
- Change the directory to api `cd api`
- Deploy to Azure App Service `az webapp up --sku S1 -n MyUniqueAppName -g MyResourceGroup -l westeurope` This will create a Resource Group, App Service Plan and App Service if they do not exist. If App Service exists, it will deploy the solution to it.
- Configure App Service startup command `az webapp config set --startup-file='gunicorn -w 2 -k uvicorn.workers.UvicornWorker main:app'`

### Setup CI/CD deployment to Azure App Service

- Install [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- Login to Azure with your credentials `az login`
- Create a resource group that you want to automatically deploy the solution to `az group create -g MyResourceGroup -l westeurope`
- Create a service credential to run the pipeline with `az ad sp create-for-rbac --name MySPNName --role Contributor --scope /subscriptions/{MySubscriptionId}/resourceGroups/{MyResourceGroup} --sdk-auth`
- In your repository, use Add secret to create a new secret named AZURE_CREDENTIALS and paste the entire JSON object produced by the az ad sp create-for-rbac command as the secret value and save the secret.
