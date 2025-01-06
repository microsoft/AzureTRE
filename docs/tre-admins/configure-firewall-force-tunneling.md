# Forced Tunneling to External Firewall in TRE

Forced tunneling ensures that all traffic from TRE is routed through a specific external firewall. This guarantees that all data passes through the firewall for inspection, control, or further processing before reaching its destination.

To setup forced tunneling to an external firewall, follow these steps:

## 1. Set the rp_bundle_values Parameter in  the config.yaml file
Provide the external firewall's IP address:

```json
rp_bundle_values: '{"firewall_force_tunnel_ip":"10.0.0.4"}'
```
This automatically creates a route table to direct TRE’s traffic to the specified IP.

## 2. Manually Connect TRE to Your Firewall
Configure connectivity between TRE’s VNet and your external firewall using one of the following methods:

1. **VNet Peering**: Peer the TRE VNet with your firewall’s VNet.
1. **ExpressRoute**: Use a private connection for firewalls located on-premises.
1. **Site-to-Site VPN**: Establish a VPN connection as an alternative.

!!! warning
    To ensure workspace-level rules can be created when TRE workspaces are provisioned without manual intervention, we highly recommend leaving the Azure TRE firewall in place. However, if all traffic must pass through a centralized enterprise firewall, forced tunneling should be configured. This enterprise firewall must also include a superset of the rules used by the TRE firewall.
