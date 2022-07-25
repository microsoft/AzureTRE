# Letsencrypt

Certain components of the TRE require the aquisition of a certificate via Letsencrypt to ensure secure HTTPS connections.

In order to aquire these certificates, there must be a public facing endpoint which can be reached by Letsencrypt.

As TREs are secured environments with very few publicly facing points, additional resources are required to ensure the certificate can be provisioned for the correct domain.

The additional resources are as followed:

1. Public IP provisioned in the same location as the web app that the certificate is intended for; this will also have a domain label which matches the web app name.
1. Storage Account with a static web app.
1. Application gateway to route traffic from the Public IP to the static web app

The following diagram illustrated the flow of data between the resources:

```mermaid
flowchart RL
    subgraph .dev Container
        direction TB
        A(letsencrypt process runs)
    end
    subgraph External
        direction TB
        B[letsencrypt authority]
    end
    subgraph TRE
        subgraph Core VNet
            C[Public IP  <br/> Domain Label: < web-app-name > <br/> Endpoint: < web-app-name >.< location >.cloudapp.net]
            subgraph Storage Account
                D[SA Static Site]
            end
        end
        subgraph VNet
            E[Key Vault <br/> kv-< tre_id >]
            subgraph VM
                F[Web App]
            end
            G[Private DNS Zone < web-app-name >.< location >.cloudapp.net]
        end
    end

    A --> |1. Request to            | B
    B --> |2. Attempts to hit       | C
    C --> |3. App Gateway routes    | D
    D --> |4. Responds              | C
    C --> |5. Responds              | B
    B --> |6. Acquires certificate  | A
    A --> |7. Stores Certificate    | E
    F --> |8. Pulls Certificate     | E
```
