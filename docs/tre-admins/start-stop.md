# Start/Stop Azure TRE

Once you've provisioned an Azure TRE instance it will begin to incurr running costs of the underlying Azure services.

Within evaluation or development, you may want to "pause" the TRE environment during out of hours or weekends, to reduce costs without having to completely destroy the environment.  The following `make targets` provide a simple way to start and stop both the Azure Firewall and Azure Application Gateway instances, considerably reducing the Azure TRE instance running costs.

!!! info
    After running `make all` underlying Azure TRE services are automatically started, billing will start.

## Start Azure TRE

This will allocate the Azure Firewall settings with a public IP and start the Azure Application Gateway service, starting billing of both services.

```bash
make tre-start
```

## Stop Azure TRE

This will deallocate the Azure Firewall public IP and stop the Azure Application Gateway service, stopping billing of both services.

```bash
make tre-stop
```
