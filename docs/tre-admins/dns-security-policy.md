# Enabling DNS Security Policy

## DNS Tunneling

A potential vector for data exfiltration is the use of a technique called DNS tunneling. Even when most outbound
network requests are blocked by firewall DNS on port 53 is required for most systems to function. DNS tunneling
works by registering a domain and running a name server that will extract data that has been encoded in the names
of DNS requests. A malisious user would need access to a workspace in order to run the client-side component of
this. Tools are readily available such as [Iodine][iodine] or [dns2tcp][dns2tcp]. Read more here about the threat
of [DNS tunnelling][dnstunneling].

## Azure DNS Security Policy

[Azure DNS security policy][azdnssec] is currently (May 2025) in public preview and enables a policy to log and
filter all DNS requests originating from a virtual network. As the service is in preview it is not enabled by
default on the TRE, but can be configured with a flag in the `config.yaml` file. Uncomment the line from the
sample config file and set `enable_dns_policy` to __`true`__.

The filters applied include an allow-list of domains that are required for basic functionality of the TRE. This list can be
seen in the [`allowed-dns.json`][allowed] file. DNS requests to all other domains are blocked. To add domain
named to the allow list, add them as list items to `allowed_dns` in the config file. Note that domains must be
fully qualified, i.e. they must end with a dot (`.`). Until `allowed-dns.json` contains a comprehensive list of required domain names, additional values may need adding to this list to the `allowed_dns` list to enable workspace services to function correctly.

To enable the service
```yaml
  enable_dns_policy: true
  allowed_dns:
    - mydomain.com.
    - anotherdomain.net.
```

When enabled, the DNS security policy always applies to the core TRE network. When a workspace is deployed there
is an optional setting "Enable DNS Security Policy" which must be checked to enrole the workspace in the policy.
If this option is not selected the workspace will be able to make DNS requests to any domain.

## Logging

When DNS security policy in enabled all DNS requests are logged to the Log Analytics workspace.

The following KQL query can be use to list DNS requests that have been blocked.

```KQL
DNSQueryLogs | where ResolverPolicyRuleAction == "None" and ResponseCode == 2
```


[dnstunneling]: https://www.paloaltonetworks.com/cyberpedia/what-is-dns-tunneling "What Is DNS Tunneling?"
[iodine]: https://code.kryo.se/iodine/
[dns2tcp]: https://www.kali.org/tools/dns2tcp/
[azdnssec]: https://learn.microsoft.com/azure/dns/dns-security-policy "DNS security policy (Preview)"
[allowed]: https://github.com/microsoft/AzureTRE/blob/main/core/terraform/allowed-dns.json
