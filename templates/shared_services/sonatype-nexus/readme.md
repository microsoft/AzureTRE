# Nexus Shared Service

This service allows users in workspaces to access external software packages in a secure manner by relying on Sonatype Nexus (RepoManager).
Documentation on Nexus can be found here: [https://help.sonatype.com/repomanager3/](https://help.sonatype.com/repomanager3/).

## Deploy

To deploy set `DEPLOY_NEXUS=true` in `templates/core/.env`.

## Configure

1. Wait for the application to come online - it can take a few minutes... and then navigate to its homepage. You can find the url by looking at the management resource group and finding a web application whose name start with nexus.
1. Retrieve the initial admin password from the "admin.password" file. You will find it by going to TRE management resource group -> storage account named "stg\<TRE-ID\>" -> "File Shares" -> "nexus-data".
1. Use the password to login to Nexus and go through the initial setup wizard. You can allow anonymous access because the purpose of this service is to use publicly available software packages.
1. On the admin screen, add **proxy** repositories as needed. Note that other types of repositories might be a way to move data in/out workspaces and you should not allow that.
1. Finally, share the repositories addresses with your users.
