import { useMsal, useAccount } from "@azure/msal-react";
import { useCallback } from "react";
import config from "./config.json";

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

    const parseJwt = (token: String) => {
        var base64Url = token.split('.')[1];
        var base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        var jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
    
        return JSON.parse(jsonPayload);
    }

    return useCallback( async (endpoint: string, method: HttpMethod, clientId?: String, body?: any, resultType?: ResultType, setRoles?: (roles: Array<String>) => void, tokenOnly?: boolean) => {
        
        if(!account) {
            console.error("No account object found, please refresh.");
            return;
        }

        const clientIdToCall = clientId || config.treApiClientId;
        const tokenResponse = await instance.acquireTokenSilent({
            scopes: [`api://${clientIdToCall}/user_impersonation`],
            account: account
        });

        config.debug && console.log("Token Response", tokenResponse);

        if(!tokenResponse) {
            console.error("Token could not be retrieved, please refresh.");
            return;
        }

        // caller can pass a function to allow us to set the roles to use for RBAC
        if(setRoles){
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
                Authorization: `Bearer ${tokenResponse.accessToken}`
            },
            method: method
        }

        // add a body if we're given one
        if (body) opts.body = JSON.stringify(body);

        try 
        {
            let resp = await fetch(`${config.treUrl}/${endpoint}`, opts);

            if (!resp.ok){
                console.error(`Error calling ${endpoint}: ${resp.status} - ${resp.statusText}`);
                return;
            }

            switch(resultType){
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
            console.error("Error calling API", err);
        }
    }, [account, instance]);
}