# Forced Tunneling to External Firewall in TRE 

Forced tunneling ensures that all traffic from TRE is routed through a specific external firewall. This guarantees that all data passes through the firewall for inspection, control, or further processing before reaching its destination.

To route TRE’s traffic through an external firewall:

##1. Set the rp_bundle_values Parameter in  the config.yaml file
Provide the external firewall's IP address:

```json
rp_bundle_values: '{"firewall_force_tunnel_ip":"10.0.0.4"}'
```
This automatically creates a route table to direct TRE’s traffic to the specified IP and deploys a public IP for firewall management.

##2. Manually Connect TRE to Your Firewall
Configure connectivity between TRE’s VNet and your external firewall using one of the following methods:

1. **VNet Peering**: Peer the TRE VNet with your firewall’s VNet.
1. **ExpressRoute**: Use a private connection for firewalls located on-premises.
1. **Site-to-Site VPN**: Establish a VPN connection as an alternative.
