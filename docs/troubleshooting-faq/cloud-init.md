# Troubleshooting cloud-init

Cloud-init is used to configure a number of virtual machines within the Azure TRE project at first boot. This methood is used as we are unable to distribute pre built images with third part dependancies. In a production environment you may choose to create your own VM images to avoid the need for cloud-init scripts to run.

Examples of virtual machines using cloud-init are:
- Resource Processor
- Sonatype Nexus VM
- Apache Guacamole Linux VM

## Retrieving the cloud-init logs
Log onto the virtual machine using Bastion or serial console and run the following command to view the cloud-init logs:

```bash
sudo cat /var/log/cloud-init-output.log
```

## Re-running cloud-init scripts
If you wish to re-run the cloud-init scripts you can run the following commands from the virtual machine terminal session:

```bash
sudo cloud-init clean --logs
sudo cloud-init init --local
sudo cloud-init init
sudo cloud-init modules --mode=config
sudo cloud-init modules --mode=final
```
