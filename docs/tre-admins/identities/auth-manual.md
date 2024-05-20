# Manually creating Microsoft Entra ID identities

This guide is here if you wanted to create these Application Registrations manually.

These should be created in order (if applicable) as some applications are then granted permission to other applications.

## Manual Creation Guides
| Application | Comments |
| ----------- | ---- |
| [Application Admin](./application_admin.md) | This is required |
| [TRE API](./api.md) | This is required |
| [UI Client](./client.md) | This is created when you create the TRE API. |
| [Automation Account](./test-account.md) | This is optional |
| [Workspace](./workspace.md)| You need one of these per Workspace if you wish to have different users in each workspace.|
