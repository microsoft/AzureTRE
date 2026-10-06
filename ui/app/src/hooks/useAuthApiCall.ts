import { AuthenticationResult, InteractionRequiredAuthError } from "@azure/msal-browser";
import { useMsal, useAccount } from "@azure/msal-react";
import { useCallback } from "react";
import { APIError, API_UNAVAILABLE_MESSAGE } from "../models/exceptions";
import config from "../config.json";

export enum ResultType {
  JSON = "JSON",
  Text = "Text",
  None = "None",
}

export enum HttpMethod {
  Get = "GET",
  Post = "POST",
  Patch = "PATCH",
  Delete = "DELETE",
}

export const useAuthApiCall = () => {
  const { instance, accounts } = useMsal();
  const account = useAccount(accounts[0] || {});

  const parseJwt = (token: string) => {
    var base64Url = token.split(".")[1];
    var base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    var jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map(function (c) {
          return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
        })
        .join(""),
    );

    return JSON.parse(jsonPayload);
  };

  return useCallback(
    async (
      endpoint: string,
      method: HttpMethod,
      workspaceApplicationIdURI?: string,
      body?: any,
      resultType?: ResultType,
      setRoles?: (roles: Array<string>) => void,
      tokenOnly?: boolean,
      etag?: string,
    ) => {
      config.debug &&
        console.log("API call", {
          endpoint: endpoint,
          method: method,
          workspaceApplicationIdURI: workspaceApplicationIdURI,
          body: body,
          resultType: resultType,
          tokenOnly: tokenOnly,
          etag: etag,
        });

      if (!account) {
        console.error("No account object found, please refresh.");
        return;
      }

      const applicationIdURI = workspaceApplicationIdURI || config.treApplicationId;
      let tokenResponse = {} as AuthenticationResult;
      let tokenRequest = {
        scopes: [`${applicationIdURI}/user_impersonation`],
        account: account,
      };

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

      // trim first slash if we're given one
      if (endpoint[0] === "/") endpoint = endpoint.substring(1);

      // default to JSON unless otherwise told
      resultType = resultType || ResultType.JSON;
      config.debug && console.log(`Calling ${method} on authenticated api: ${endpoint}`);

      // set the headers for auth + http method
      const opts: RequestInit = {
        mode: "cors",
        headers: {
          Authorization: `Bearer ${tokenResponse.accessToken}`,
          "Content-Type": "application/json",
          etag: etag ? etag : "",
        },
        method: method,
      };

      // add a body if we're given one
      if (body) opts.body = JSON.stringify(body);

      const controller = new AbortController();
      // The timeout covers the whole call, including reading the response body.
      const timeout = window.setTimeout(() => controller.abort(), 30000);
      const unavailableError = (err: any) => {
        const e = new APIError();
        e.name = "API call failure";
        e.message = err?.message || "Unable to reach the TRE API";
        e.status = controller.signal.aborted || err?.name === "AbortError" ? 408 : 503;
        e.userMessage = API_UNAVAILABLE_MESSAGE;
        e.endpoint = `${config.treUrl}/${endpoint}`;
        e.stack = err?.stack;
        e.exception = err instanceof Error ? err.message : String(err);
        return e;
      };
      try {
        let resp;
        try {
          opts.signal = controller.signal;
          resp = await fetch(`${config.treUrl}/${endpoint}`, opts);
        } catch (err: any) {
          throw unavailableError(err);
        }

        if (!resp.ok) {
          let e = new APIError();
          try {
            e.message = await resp.text();
          } catch (err: any) {
            if (controller.signal.aborted) throw unavailableError(err);
            throw err;
          }
          e.status = resp.status;
          e.endpoint = endpoint;
          if (resp.status === 408 || resp.status === 429 || resp.status >= 500) {
            e.userMessage = API_UNAVAILABLE_MESSAGE;
          }
          throw e;
        }

        try {
          switch (resultType) {
            case ResultType.Text:
              let text = await resp.text();
              config.debug && console.log(text);
              return text;
            case ResultType.JSON:
              let json = await resp.json();
              config.debug && console.log(json);
              return json;
            case ResultType.None:
              return;
          }
        } catch (err: any) {
          if (controller.signal.aborted) throw unavailableError(err);
          let e = err as APIError;
          e.name = "Error with response data";
          throw e;
        }
      } finally {
        window.clearTimeout(timeout);
      }
    },
    [account, instance],
  );
};
