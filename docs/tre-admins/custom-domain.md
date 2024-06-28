# Custom domain name

In order to use a custom domain name with the Azure TRE:

1. Register a domain name, and create a DNS entry for the domain name pointing to the FQDN of the Azure App Gateway, e.g. `mytre-domain-name.org.  CNAME  mytre.region.cloudapp.azure.com.`

2. Set the domain name in the `CUSTOM_DOMAIN` variable in `config.yaml` or create a GitHub Actions secret, depending on your deployment method.

3. Update the *TRE UX* App Registration redirect URIs:

   a. If you haven't deployed your TRE yet, this is done automatically for you using the `make auth` command.  Refer to the setup instructions to deploy your TRE.

   b. If your TRE has already been deployed, manually add the following redirect URIs in Entra ID > App Registrations > *TRE_ID UX* > Authentication > Single-page application Redirect URIs:

```text
  https://mytre-domain-name.org
  https://mytre-domain-name.org/api/docs/oauth2-redirect
```

4. Generate an SSL certificate for the TRE's new domain name:

```bash
  make letsencrypt
```

## Limitations

The method above allows a custom domain name to be used to access the Azure TRE's portal and Swagger UI.  It does not configure the custom domain name for Guacamole instances, or services available within the TRE network such as Gitea, or Sonatype Nexus.
