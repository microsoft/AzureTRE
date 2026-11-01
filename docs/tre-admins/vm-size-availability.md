# VM Size Availability

Azure does not offer all VM sizes in all regions. Azure can also block a size for a subscription in a region. If a template uses a size that the region does not offer, the deployment fails.

The script `devops/scripts/vm_size_report.py` finds each VM size in the repository. Then it shows the status of each size in one or more regions, for your subscription.

## Run the script by hand

You need:

- A clone of the repository. The script reads the files that git tracks.
- Python 3 and the Azure CLI. The [development container](setup-instructions/prerequisites.md#development-container) has both.
- The Reader role on the subscription.

1. Log in to Azure with `az login`.
1. Select the subscription with `az account set --subscription <subscription-id>`. You can also give the script the option `--subscription <subscription-id>`.
1. In the repository root, run the script with one or more regions:

    ```bash
    python3 devops/scripts/vm_size_report.py --region switzerlandnorth --output vm-size-report.md
    ```

To check more than one region, separate the regions with commas, for example `--region switzerlandnorth,uksouth`. One region takes about 1 minute. More regions take about 1.5 minutes in total, because the script gets the data for all regions in one query.

If you do not give a region, the script checks the names against the catalogue only. It does not use Azure.

## Run the GitHub workflow

1. In GitHub, open **Actions** and select **VM Size Availability**.
1. Select **Run workflow**.
1. In **Region**, select a region. The default `ci-location` is the `LOCATION` variable of the `CICD` environment.
1. To check more regions, type them in **More regions**, separated by commas. To check only these regions, select `none` in **Region**.

You can also start the workflow with the GitHub CLI:

```bash
gh workflow run vm_size_report.yml -f region=none -f more_regions=uksouth,eastus2
```

The workflow logs in to Azure with the identity of the `CICD` environment. The report shows on the summary page of the run. The report is also in the `vm-size-report` artifact for 7 days. The workflow leaves the subscription out of the report, because anyone can see the run of a public repository.

GitHub shows **Run workflow** only when the workflow file is on the default branch.

### Runs on a branch push

The workflow also starts on a push to a branch other than `main`, if the push changes one of these files:

- The files that set VM sizes in code: `porter.yaml`, `template_schema.json` and Terraform files in `templates`, the files in `core/terraform`, `config_schema.json` and the action `devcontainer_run_command`.
- The files of the report: the script, the catalogue and the workflow.

A run on a push checks the `LOCATION` region of the `CICD` environment. A new push to the same branch stops the older run. The workflow does not start on pull requests.

## Read the report

The report has a column for each region. Problems come first. In each status, sizes that the code uses come before sizes that only samples, tests or documents use.

The **Service** column shows what uses the size:

- **VM**: a virtual machine or a scale set. The script uses the VM SKU list of the region, with the restrictions for your subscription.
- **AML cluster** and **AML instance**: an Azure Machine Learning compute cluster or compute instance. Azure ML has its own list of sizes for each region, and does not use the VM restrictions. The script uses that list.

A size can have a different status for each service. For example, the VM SKU list can block `Standard_DS2_v2` for your subscription, but Azure ML can still offer it for a compute cluster.

| Status | Meaning |
| --- | --- |
| ❓ Unknown name | The name is not in the Azure catalogue. The size is retired or the name is wrong. |
| ⛔ Blocked | The region has the size, but the subscription cannot use it. |
| ❌ Not offered | The region does not have the size for this service. |
| ⚠️ Some zones blocked | The subscription can use the size, but not in the zones shown. |
| ➖ Not checked | The script could not get the Azure ML sizes of the region. The script prints the reason. |
| ✅ Available | The subscription can use the size in the region. |
| ✔️ In catalogue | The name is in the Azure catalogue. The report did not check a region. |

The report does not check quota. A size can be available and still have no free quota. Azure ML has a separate quota.

## Refresh the catalogue

The file `devops/scripts/vm_size_catalogue.txt` lists all VM sizes that Azure offers in any region. Azure removes retired sizes from its API. For this reason, the script finds names that look like VM sizes, and uses the catalogue to identify names that do not exist.

To refresh the catalogue, run:

```bash
python3 devops/scripts/vm_size_report.py --refresh-catalogue
```

The query takes about 1.5 minutes.
