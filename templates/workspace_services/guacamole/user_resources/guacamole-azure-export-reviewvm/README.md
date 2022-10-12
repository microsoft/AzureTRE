# How to work with this template

This template is based off another user resource template, [guacamole-azure-windowsvm](../guacamole-azure-windowsvm/) (reference template).

They share much of terraform configuration. Instead of copying the terraform configuration into this directory and having to maintain multiple copies of it over time, the reference configuration is checked out at the time of building the bundle, and a [patch](./windowsvm.patch) is applied.

Note that the patch is applied only to files in terraform directory. All the other files that don't already exist in this template are borrowed from the reference template as-is.

## How to make a change to terraform configuration

Follow this set of steps:

1. Run [apply_patch.sh](./apply_patch.sh) script from the root directory of the bundle to check out the reference terraform configuration and apply the existing patch to it.

1. Comment out line in [Dockerfile.tmpl](./Dockerfile.tmpl) that calls `apply_patch.sh`.

1. Now you can use the bundle as normal. You can build, deploy it and test your changes.

1. When you are ready to submit the pull request, you need to create a new patch. Run [create_patch.sh](./create_patch.sh) from the root directory of the bundle. This will create a patch but _it will delete the terraform files you were working with_. 

1. Add the patch file, [windowsvm.patch](./windowsvm.patch) to your pull request, along with any other changes.

1. Submit a pull request. Make sure you aren't adding any files from [terraform](./terraform/) directory, other than [empty.txt](./terraform/empty.txt), as this would break the process of creating patches. Also make sure you aren't adding any files in the root template directory that already exist in the reference template.

### How to upgrade the version of the reference configuration.

1. Change the version used in [apply_patch.sh](./apply_patch.sh).

1. Run [apply_patch.sh](./apply_patch.sh) script. It may fail as the patch was created for an older version of the configuration. Manually resolve any conflicts.

1. Comment out line in [Dockerfile.tmpl](./Dockerfile.tmpl) that calls `apply_patch.sh` that you just ran.

1. Test that the bundle still works as intended (at the minimum, deploy it and check for errros).

1. Change the version used in [create_patch.sh](./create_patch.sh) to match the one in `apply_patch.sh`, then run it to create a new patch.

1. Change the version used in [Dockerfile.tmpl](./Dockerfile.tmpl) to match the one in `apply_patch.sh`.

1. Submit a pull request. Make sure you aren't adding any files from [terraform](./terraform/) directory, other than [empty.txt](./terraform/empty.txt), as this would break the process of creating patches. Also make sure you aren't adding any files in the root template directory that already exist in the reference template.
