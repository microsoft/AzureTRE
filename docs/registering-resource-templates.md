# Registering Resource Templates

Before a resource template can be deployed using the API it needs to be registered.

## Porter Bundles

To register Porter bundles with the TRE a utility script is provided at: [../devops/scripts/publish_register_bundle.sh](../devops/scripts/publish_register_bundle.sh).

The script needs to be executed from within the bundle directory, for example `/workspaces/azureml_devtestlabs/`. This script can be used as follows:

```cmd
    Usage: ../../devops/scripts/publish_register_bundle.sh [-u --tre_url]  [-c --current] [-i --insecure]

    Options:
        -u, --tre_url:        URL for the TRE
        -r, --acr-name        Azure Container Registry Name
        -t, --bundle-type     Bundle type, workspace
        -c, --current:        Make this the currently deployed version of this template
        -i, --insecure:       Bypass SSL certificate checks
```

The script does three things:

1. Publishes the bundle to the Azure Container Registry specified.

1. Extracts the parameters from the bundle using `porter explain`.

1. Posts the details of the bundle to the `/api/workspace-templates` endpoint.

Once registered the template can be retrieved by a `GET` operation on `/api/workspace-templates`.
