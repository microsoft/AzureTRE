# Forced Tunneling to External Firewall in TRE

Azure TRE deploys and manages an Azure firewall to ensure creation of workspace level rules can be automated when TRE workspaces and other services are created without manual intervention.
It is highly recommended leaving the Azure TRE firewall in place. If there is still the requirement to send all traffic through a centralized enterprise firewall, such as that deployed as part of an Azure landing zone, then forced tunnelling should be used. The centralized firewall will need a superset of rules used by the TRE.

To setup forced tunneling to an external firewall, follow these steps:

## 1. Set the firewall_force_tunnel_ip parameter in the config.yaml file
Provide the external firewall's IP address:

```json
firewall_force_tunnel_ip: 192.168.0.4
```
This automatically creates a route table to direct TRE’s traffic to the specified IP.

## 2. Manually Connect TRE to Your Firewall
Configure connectivity between TRE’s VNet and your external firewall using one of the following methods:

1. **VNet Peering**: Peer the TRE VNet with your firewall’s VNet.
1. **ExpressRoute**: Use a private connection for firewalls located on-premises.
1. **Site-to-Site VPN**: Establish a VPN connection as an alternative.
