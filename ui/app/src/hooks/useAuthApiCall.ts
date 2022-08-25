import { AuthenticationResult, InteractionRequiredAuthError } from "@azure/msal-browser";
import { useMsal, useAccount } from "@azure/msal-react";
import { useCallback } from "react";
import config from "../config.json";

export enum ResultType {
    JSON = "JSON",
    Text = "Text",
    None = "None"
}

export enum HttpMethod {
    Get = "GET",
    Post = "POST",
    Patch = "PATCH",
    Delete = "DELETE"
}

export const useAuthApiCall = () => {
    const { instance, accounts } = useMsal();
    const account = useAccount(accounts[0] || {});

    const parseJwt = (token: string) => {
        var base64Url = token.split('.')[1];
        var base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        var jsonPayload = decodeURIComponent(atob(base64).split('').map(function (c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));

        return JSON.parse(jsonPayload);
    }

    return useCallback(async (
        endpoint: string,
        method: HttpMethod,
        workspaceApplicationIdURI?: string,
        body?: any,
        resultType?: ResultType,
        setRoles?: (roles: Array<string>) => void,
        tokenOnly?: boolean,
        etag?: string) => {

        if (!account) {
            console.error("No account object found, please refresh.");
            return;
        }

        const applicationIdURI = workspaceApplicationIdURI || config.treApplicationId;
        let tokenResponse = {} as AuthenticationResult;
        let tokenRequest = {
            scopes: [`${applicationIdURI}/user_impersonation`],
            account: account
        }

        // try and get a token silently. at times this might throw an InteractionRequiredAuthError - if so give the user a popup to click
        try {
            tokenResponse = await instance.acquireTokenSilent(tokenRequest);
        } catch (err) {
            console.warn("Unable to get a token silently", err);
            if (err instanceof InteractionRequiredAuthError) {
                tokenResponse = await instance.acquireTokenPopup(tokenRequest);
            }
        }

        config.debug && console.log("Token Response", tokenResponse);

        if (!tokenResponse) {
            console.error("Token could not be retrieved, please refresh.");
            return;
        }

        // caller can pass a function to allow us to set the roles to use for RBAC
        if (setRoles) {
            let decodedToken = parseJwt(tokenResponse.accessToken);
            config.debug && console.log("Decoded token", decodedToken);
            setRoles(decodedToken.roles);
        }

        // we might just want the token to get the roles.
        if (tokenOnly) return;

        // default to JSON unless otherwise told
        resultType = resultType || ResultType.JSON;
        config.debug && console.log(`Calling ${method} on authenticated api: ${endpoint}`);

        // set the headers for auth + http method
        const opts: RequestInit = {
            mode: "cors",
            headers: {
                Authorization: `Bearer ${tokenResponse.accessToken}`,
                'Content-Type': 'application/json',
                'etag': etag ? etag : ""
            },
            method: method
        }

        // add a body if we're given one
        if (body) opts.body = JSON.stringify(body);

        try {
            let resp = await fetch(`${config.treUrl}/${endpoint}`, opts);

            if (!resp.ok) {
                let message = `Error calling ${endpoint}: ${resp.status} - ${resp.statusText}`
                throw(message);
            }

            switch (resultType) {
                case ResultType.Text:
                    let text = await resp.text();
                    config.debug && console.log(text);
                    return text;
                case ResultType.JSON:
                    let json = await resp.json();
                    config.debug && console.log(json);
                    return json
                case ResultType.None:
                    return;
            }
        } catch (err: any) {
            // TODO: this is currently hiding errors, we should either rethrow to be handled in components
            // or hook this up to user-facing alerts
            console.error("Error calling API", err);
            throw err;
        }
    }, [account, instance]);
}
