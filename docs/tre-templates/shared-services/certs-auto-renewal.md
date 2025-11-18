# Certificate Service Auto-Renewal

The Certificate Service provides automatic certificate renewal capabilities to ensure your TRE certificates remain valid without manual intervention.

## Overview

Starting with certificate service version 0.8.0, the service can automatically monitor certificate expiry dates and trigger renewal when certificates are approaching expiration. This feature is particularly useful for:

- Main TRE web and API certificates
- Nexus service certificates  
- Any other certificates managed by the certificate service

## How It Works

The auto-renewal feature uses Azure Logic Apps to:

1. **Monitor**: Periodically check certificate expiry dates in Key Vault
2. **Evaluate**: Compare expiry dates against the configured renewal threshold
3. **Renew**: Automatically trigger certificate renewal via the TRE API when needed
4. **Log**: Record all renewal activities for monitoring and auditing

## Configuration

When deploying the certificate service, you can enable auto-renewal with the following parameters:

### Enable Auto-renewal
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable automatic renewal of the certificate before expiry
- **Updateable**: Yes

### Renewal Threshold (days)
- **Type**: Integer
- **Default**: `30`
- **Range**: 1-60 days
- **Description**: Number of days before expiry to trigger renewal
- **Updateable**: Yes

### Renewal Schedule (cron)
- **Type**: String
- **Default**: `"0 2 * * 0"` (Weekly on Sunday at 2 AM)
- **Description**: Cron expression for checking certificate expiry
- **Updateable**: Yes

## Deployment Example

When deploying the certificate service via the TRE UI or API, enable auto-renewal like this:

```json
{
  "templateName": "tre-shared-service-certs",
  "properties": {
    "display_name": "Certificate Service with Auto-renewal",
    "description": "SSL certificate service with automatic renewal",
    "domain_prefix": "nexus",
    "cert_name": "nexus-ssl",
    "enable_auto_renewal": true,
    "renewal_threshold_days": 30,
    "renewal_schedule_cron": "0 2 * * 0"
  }
}
```

## Monitoring

The auto-renewal system provides several monitoring capabilities:

### Logic App Logs
- View execution history in the Azure portal
- Monitor success/failure of renewal checks
- Access detailed logs for troubleshooting

### Certificate Outputs
The service outputs additional information when auto-renewal is enabled:

- `auto_renewal_enabled`: Whether auto-renewal is active
- `auto_renewal_logic_app_name`: Name of the Logic App handling renewal
- `renewal_threshold_days`: Current renewal threshold setting

### Alerting
You can set up Azure Monitor alerts on the Logic App to notify administrators of:
- Failed certificate checks
- Failed renewal attempts
- Successful certificate renewals

## Security Considerations

The auto-renewal feature uses managed identities and follows security best practices:

### Permissions
The Logic App is granted minimal required permissions:
- **Key Vault Certificates Officer**: To read certificate expiry dates
- **Contributor**: To trigger TRE API operations (scoped to resource group)

### Network Access
- Logic App communicates with Key Vault and TRE API over HTTPS
- Uses Azure's internal network where possible
- No external dependencies beyond Let's Encrypt (same as manual renewal)

## Troubleshooting

### Common Issues

1. **Logic App not triggering renewals**
   - Check the Logic App execution history in Azure portal
   - Verify the cron schedule is correct
   - Ensure the Logic App has proper permissions

2. **Certificate not found errors**
   - Verify the certificate name matches exactly
   - Check that the certificate exists in Key Vault
   - Confirm the Logic App has Key Vault access

3. **API authentication failures**
   - Ensure the Logic App managed identity has appropriate TRE permissions
   - Verify the TRE API endpoint is accessible
   - Check for API rate limiting or other restrictions

### Manual Intervention

If auto-renewal fails, you can always fall back to manual renewal:

1. Via TRE API: `POST /api/shared-services/{service-id}/invoke-action?action=renew`
2. Via TRE UI: Navigate to the certificate service and trigger the "Renew" action

## Upgrading Existing Certificates

To enable auto-renewal on existing certificate services:

1. Upgrade the certificate service to version 0.8.0 or later
2. Update the service properties to enable auto-renewal:
   ```json
   {
     "enable_auto_renewal": true,
     "renewal_threshold_days": 30,
     "renewal_schedule_cron": "0 2 * * 0"
   }
   ```

!!! note
    Upgrading to enable auto-renewal will deploy a new Logic App but won't affect existing certificates or cause downtime.

## Best Practices

1. **Threshold Selection**: Set renewal threshold to at least 7 days to allow time for troubleshooting if renewal fails
2. **Schedule Frequency**: Weekly checks are usually sufficient; daily checks may be needed for high-turnover environments
3. **Monitoring**: Set up alerts for Logic App failures to catch issues early
4. **Testing**: Test auto-renewal in development environments before enabling in production
5. **Documentation**: Keep track of which certificates have auto-renewal enabled

## Limitations

- Auto-renewal uses the same Let's Encrypt rate limits as manual renewal
- Requires the certificate service to be deployed and healthy
- Logic App execution depends on Azure Logic Apps service availability
- Cannot renew certificates that are already expired (manual intervention required)

## Support

For issues with auto-renewal:

1. Check the Logic App execution history and logs
2. Review this documentation and troubleshooting section
3. Contact your TRE administrator or Azure support team
4. As a fallback, use manual certificate renewal procedures