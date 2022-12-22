# Guacamole Authorization Extension

This extension is built (maven) and is placed inside the extension directory.
Guacamole tries to authorize using all the given extensions.
Read more [here](https://guacamole.apache.org/doc/gug/guacamole-ext.html).

## TRE Authorization extension

This extension works in the following manner:

1. receives a token from the OpenId extension
2. The extension call the project api to get the user's vm list
3. When connect request is made, the extension call the project api to get the password to the selected vm and inject it into the Guacamole configurations.

## OAuth2 Proxy


- The extention uses [OAuth2_Proxy](https://github.com/oauth2-proxy/oauth2-proxy) which is a reverse proxy and static file server that provides authentication using Providers to validate accounts by email, domain or group.
- The current version that is being used is **7.4.0.**
- The main file that controls the behavior of the oauth2 proxy is the [run](/workspaces/AzureTRE/templates/workspace_services/guacamole/guacamole-server/docker/services/oauth/run) file, which contains all the runtime arguments.
- Some important notes on the way we use the oauth2 proxy:
  - Guacamole auth extention uses the generic provider (oidc) since the Azure provider is broken in the proxy repository.
  - When upgraded to version 7.4.0, \
  `--insecure-oidc-allow unverified-email true,
   --oidc-groups-claim "roles"` were added becaue of this following [issue](https://github.com/oauth2-proxy/oauth2-proxy/issues/1680).
