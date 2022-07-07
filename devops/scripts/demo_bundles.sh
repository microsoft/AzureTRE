# shared services
make bundle-build DIR=templates/shared_services/cyclecloud
make bundle-publish DIR=templates/shared_services/cyclecloud
make bundle-register DIR=templates/shared_services/cyclecloud BUNDLE_TYPE=shared_service

make bundle-build DIR=templates/shared_services/sonatype-nexus-vm
make bundle-publish DIR=templates/shared_services/sonatype-nexus-vm
make bundle-register DIR=templates/shared_services/sonatype-nexus-vm BUNDLE_TYPE=shared_service

# workspaces

make bundle-build DIR=templates/workspaces/base
make bundle-publish DIR=templates/workspaces/base
make bundle-register DIR=templates/workspaces/base BUNDLE_TYPE=workspace

# workspace services
make bundle-build DIR=templates/workspace_services/azureml
make bundle-publish DIR=templates/workspace_services/azureml
make bundle-register DIR=templates/workspace_services/azureml BUNDLE_TYPE=workspace_service

make bundle-build DIR=templates/workspace_services/guacamole
make bundle-publish DIR=templates/workspace_services/guacamole
make bundle-register DIR=templates/workspace_services/guacamole BUNDLE_TYPE=workspace_service

make bundle-build DIR=templates/workspace_services/gitea
make bundle-publish DIR=templates/workspace_services/gitea
make bundle-register DIR=templates/workspace_services/gitea BUNDLE_TYPE=workspace_service


make bundle-build DIR=templates/workspace_services/mlflow
make bundle-publish DIR=templates/workspace_services/mlflow
make bundle-register DIR=templates/workspace_services/mlflow BUNDLE_TYPE=workspace_service

make bundle-build DIR=templates/workspace_services/galaxy-webapp
make bundle-publish DIR=templates/workspace_services/galaxy-webapp
make bundle-register DIR=templates/workspace_services/galaxy-webapp BUNDLE_TYPE=workspace_service

make bundle-build DIR=templates/workspace_services/innereye
make bundle-publish DIR=templates/workspace_services/innereye
make bundle-register DIR=templates/workspace_services/innereye BUNDLE_TYPE=workspace_service

make bundle-build DIR=templates/workspace_services/cyclecloud
make bundle-publish DIR=templates/workspace_services/cyclecloud
make bundle-register DIR=templates/workspace_services/cyclecloud BUNDLE_TYPE=workspace_service

# user resources

make bundle-build DIR=templates/workspace_services/guacamole/user_resources/guacamole-azure-linuxvm
make bundle-publish DIR=templates/workspace_services/guacamole/user_resources/guacamole-azure-linuxvm
make bundle-register DIR=templates/workspace_services/guacamole/user_resources/guacamole-azure-linuxvm BUNDLE_TYPE=user_resource WORKSPACE_SERVICE_NAME=tre-service-guacamole

make bundle-build DIR=templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm
make bundle-publish DIR=templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm
make bundle-register DIR=templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm BUNDLE_TYPE=user_resource  WORKSPACE_SERVICE_NAME=tre-service-guacamole

make bundle-build DIR=templates/workspace_services/guacamole/user_resources/aml_compute
make bundle-publish DIR=templates/workspace_services/guacamole/user_resources/aml_compute
make bundle-register DIR=templates/workspace_services/azureml/user_resources/aml_compute BUNDLE_TYPE=user_resource WORKSPACE_SERVICE_NAME=tre-service-azureml
