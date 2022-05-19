# Introduction


```sh
make terraform-deploy DIR=./templates/workspace_services/ohdsi/
```

```sh
make bundle-build DIR=./templates/workspace_services/ohdsi/
```

```sh
make bundle-install DIR=./templates/workspace_services/ohdsi/
```

```sh
porter invoke [INSTALLATION] --action ACTION [flags] 
porter invoke tre-service-ohdsi-installer --action docker_stuff --debug
```
