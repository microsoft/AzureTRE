import { Configuration,  PublicClientApplication } from "@azure/msal-browser";
import config from "./config.json"

// MSAL configuration
const configuration: Configuration = {
    auth: {
        clientId: config.rootClientId,
        authority: `https://login.microsoftonline.com/${config.rootTenantId}`,
        redirectUri: `${window.location.protocol}//${window.location.hostname}:${window.location.port}`,
        postLogoutRedirectUri: `${window.location.protocol}//${window.location.hostname}:${window.location.port}/logout`
    }
};

export const pca = new PublicClientApplication(configuration);