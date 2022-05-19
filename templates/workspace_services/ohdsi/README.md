# Introduction


```bash
make terraform-deploy DIR=./templates/workspace_services/ohdsi/
```

```bash
make bundle-build DIR=./templates/workspace_services/ohdsi/
```

```bash
make bundle-install DIR=./templates/workspace_services/ohdsi/
```

```bash
porter invoke [INSTALLATION] --action ACTION [flags] 
porter invoke tre-service-ohdsi-installer --action docker_stuff --debug
```
