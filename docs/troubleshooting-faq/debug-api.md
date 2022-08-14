# Enabling DEBUG mode on the API

The API is by default configured to not show detailed error messages and stack trace when an error occurs. This is done to prevent leaking internal state to the outside world and to minimize information which an attacker could use against the deployed instance.

However, you can enable debugging, by setting `DEBUG=true` in the configuration settings of the API using Azure portal.

1. Go to App Service for the API and select **Settings > Configuration**.
1. Click **New Application Setting**.
1. in the new dialog box set **Name=DEBUG** and **Value=true**