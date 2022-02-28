/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.apache.guacamole.auth.azuretre;

import com.auth0.jwk.Jwk;
import com.auth0.jwk.UrlJwkProvider;
import com.auth0.jwt.JWT;
import com.auth0.jwt.JWTVerifier;
import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.interfaces.Claim;
import com.auth0.jwt.interfaces.DecodedJWT;
import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.net.auth.credentials.CredentialsInfo;
import org.apache.guacamole.net.auth.credentials.GuacamoleInvalidCredentialsException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


import java.net.MalformedURLException;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CancellationException;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;

import javax.servlet.http.HttpServletRequest;

import com.microsoft.aad.msal4j.AuthorizationCodeParameters;
import com.microsoft.aad.msal4j.AuthorizationRequestUrlParameters;
import com.microsoft.aad.msal4j.ClientCredentialFactory;
import com.microsoft.aad.msal4j.IClientSecret;
import com.microsoft.aad.msal4j.IConfidentialClientApplication;
import com.microsoft.aad.msal4j.ConfidentialClientApplication;
import com.microsoft.aad.msal4j.ResponseMode;
import com.nimbusds.oauth2.sdk.AuthorizationCode;
import com.nimbusds.oauth2.sdk.ParseException;
import com.microsoft.aad.msal4j.IAuthenticationResult;
import com.nimbusds.openid.connect.sdk.AuthenticationErrorResponse;
import com.nimbusds.openid.connect.sdk.AuthenticationResponse;
import com.nimbusds.openid.connect.sdk.AuthenticationResponseParser;
import com.nimbusds.openid.connect.sdk.AuthenticationSuccessResponse;

import org.apache.guacamole.net.auth.Credentials;
import org.apache.guacamole.form.RedirectField;
import org.apache.guacamole.language.TranslatableMessage;
import org.apache.guacamole.auth.azuretre.user.TreUser;


import java.security.interfaces.RSAPublicKey;

public class AuthenticationProviderService {

    private static final Logger LOGGER = LoggerFactory.getLogger(AuthenticationProviderService.class);
    private static final String PARAMETER_NAME = "id_token";
    private static final String STATE = "state";

    private final TreAuthenticationProvider authenticationProvider;
    private final TreProperties configuration;
    private final OAuthVerifier oauthStateVerifier = new OAuthVerifier();
    private final String clientId;
    private final String clientSecret;
    private final URI authority;
    private final Set<String> scopes;
    private final URI redirectUri;

    public AuthenticationProviderService(TreAuthenticationProvider authenticationProvider) throws GuacamoleException {
        LOGGER.info("Loading config.");

        this.authenticationProvider = authenticationProvider;
        configuration = new TreProperties();

        clientId = configuration.getClientId();
        authority = configuration.getAuthority();
        clientSecret = configuration.getClientSecret();
        redirectUri = configuration.getRedirectUri();

        // Convert space-separated
        String scope = configuration.getScope();
        this.scopes = new HashSet<>(Arrays.asList(scope.split(" ")));

        LOGGER.info("Client Id = " + clientId);
    }


	public TreUser authenticateUser(Credentials credentials) throws GuacamoleException {

		HttpServletRequest request = credentials.getRequest();

		// If this is a redirect from Azure AD then process the authentication code and
		// return the authenticated user.
		if (isOidcRedirect(request)) {
			return processAuthenticationCodeRedirect(request, credentials);
		}

		// Otherwise, we're not authenticated so create the redirect to Azure AD for the
		// user to sign in.

		// Code challenge is needed for PKCE.
		CodeChallengeState state = oauthStateVerifier.createCodeChallenge();

		AuthorizationRequestUrlParameters parameters = AuthorizationRequestUrlParameters
				.builder(redirectUri.toString(), scopes).responseMode(ResponseMode.QUERY).state(state.getId())
				.codeChallengeMethod(state.getChallengeMethod()).codeChallenge(state.getCodeChallenge()).build();

		final IConfidentialClientApplication client = getConfidentialClientInstance();

		URI authReq;
		try {
			authReq = client.getAuthorizationRequestUrl(parameters).toURI();
		} catch (final URISyntaxException ex) {
			throw new GuacamoleException(new TranslatableMessage("LOGIN.ERROR_CONFIG").toString());
		}

		// Request OpenID token
		throw new GuacamoleInvalidCredentialsException("Invalid login.", new CredentialsInfo(Arrays.asList(
				// OpenID-specific token (will automatically redirect the user to the
				// authorization page via JavaScript)
				new RedirectField(PARAMETER_NAME, authReq,
						new TranslatableMessage("LOGIN.INFO_OID_REDIRECT_PENDING")))));
	}

	/**
	 * Gets the {@link IConfidentialClientApplication}. For details see
	 * https://aka.ms/msal4jclientapplications
	 * 
	 * @return The client object.
	 * @throws GuacamoleException
	 */
	public IConfidentialClientApplication getConfidentialClientInstance() throws GuacamoleException {
		ConfidentialClientApplication confClientInstance = null;

		LOGGER.info("Client Id = " + this.clientId);
		try {
			final IClientSecret secret = ClientCredentialFactory.createFromSecret(this.clientSecret);
			confClientInstance = ConfidentialClientApplication.builder(this.clientId, secret)
					.authority(this.authority.toString()).build();
		} catch (final MalformedURLException ex) {
			LOGGER.error("MalformedURLException thrown creating the MSAL Client app", ex);
			throw new GuacamoleException(new TranslatableMessage("LOGIN.ERROR_CONFIG").toString());
		}

		return confClientInstance;
	}

	/**
	 * Check the HTTP request to see if it is an response from an Open ID Connect
	 * authorization redirect.
	 * 
	 * @param request The HTTP request.
	 * @return True, if the request can be parsed as an authentication response,
	 *         otherwise False.
	 */
	private Boolean isOidcRedirect(HttpServletRequest request) {
		if (request.getParameterMap().size() == 0) {
			return false;
		}

		// We've got query parameters, can these be parsed to an OIDC redirect?
		try {
			Map<String, List<String>> params = getRequestParameters(request);

			AuthenticationResponse resp = AuthenticationResponseParser.parse(redirectUri, params);
			return resp.getState() != null;
		} catch (ParseException e) {
			return false;
		}
	}

	private Map<String, List<String>> getRequestParameters(HttpServletRequest request) {
		Map<String, List<String>> params = new HashMap<>();

		@SuppressWarnings("unchecked")
		Set<String> keys = request.getParameterMap().keySet();

		for (String key : keys) {
			String[] paramValue = (String[]) request.getParameterMap().get(key);
			params.put(key, Collections.singletonList(paramValue[0]));
		}

		return params;
	}

	/**
	 * Processes the authentication code response. There should be two parameters,
	 * state and code. The state is used to look up the stored state, and must be
	 * valid (state will time out after 10 min). The code is them used to request
	 * access, id and refresh tokens.
	 * 
	 * @param request     The HTTP request object.
	 * @param credentials The Guacamole credentials object.
	 * @return An authenticated {@link TreUser} object.
	 * @throws GuacamoleException
	 */
	private TreUser processAuthenticationCodeRedirect(HttpServletRequest request, Credentials credentials)
			throws GuacamoleException {
		Map<String, List<String>> params = getRequestParameters(request);

		// Verify the state.
		String returnedStateId = params.get(STATE).get(0);
		CodeChallengeState state = oauthStateVerifier.getState(returnedStateId);
		if (state == null) {
			throw new GuacamoleException("Invalid OAuth state.");
		}

		try {
			AuthenticationResponse authResponse = AuthenticationResponseParser.parse(redirectUri, params);
			if (authResponse instanceof AuthenticationSuccessResponse) {
				AuthenticationSuccessResponse oidcResponse = (AuthenticationSuccessResponse) authResponse;

				if (oidcResponse.getIDToken() != null || oidcResponse.getAccessToken() != null
						|| oidcResponse.getAuthorizationCode() == null) {
					throw new GuacamoleException("unexpected set of artifacts received");
				}

				return getTreUserByAuthCode(request, credentials, oidcResponse.getAuthorizationCode(), state);
			}
			if (authResponse instanceof AuthenticationErrorResponse) {
				AuthenticationErrorResponse oidcResponse = (AuthenticationErrorResponse) authResponse;
				throw new GuacamoleInvalidCredentialsException(oidcResponse.getErrorObject().getDescription(),
						CredentialsInfo.EMPTY);
			}
			throw new GuacamoleException("Invalid authorization response.");
		} catch (ParseException ex) {
			throw new GuacamoleException("Failed to processed parameters in the oauth response.");
		}
	}

	/**
	 * Uses the authorisation code and the PKCE code challenge (stored in the state)
	 * to acquire access and id tokens from Azure AD.
	 * 
	 * @param request           The HTTP request object.
	 * @param credentials       The Guacamole credentials object.
	 * @param authorizationCode The authorization code extracted from the request
	 *                          parameters.
	 * @param state             The state that was created when the redirect to
	 *                          Azure AD was made.
	 * @return An authenticated {@link TreUser} object.
	 * @throws GuacamoleException
	 */
	TreUser getTreUserByAuthCode(HttpServletRequest request, Credentials credentials,
			AuthorizationCode authorizationCode, CodeChallengeState state) throws GuacamoleException {
		try {
			IConfidentialClientApplication app = getConfidentialClientInstance();

			String authCode = authorizationCode.getValue();

			AuthorizationCodeParameters parameters = AuthorizationCodeParameters.builder(authCode, this.redirectUri)
					.scopes(scopes).codeVerifier(state.getCodeVerifier()).build();

			Future<IAuthenticationResult> future = app.acquireToken(parameters);

			IAuthenticationResult result = future.get();

			if (result == null) {
				throw new GuacamoleException("authentication result was null");
			}

			return new TreUser(this.authenticationProvider, credentials, result, app.tokenCache());

		} catch (ExecutionException | CancellationException | InterruptedException ex) {
			throw new GuacamoleException(ex.getCause().getMessage());
		}
	}

    public void validateToken(final String token, final UrlJwkProvider jwkProvider)
        throws GuacamoleInvalidCredentialsException {

        try {
            if (System.getenv("AUDIENCE").length() == 0) {
                throw new Exception("AUDIENCE is not provided");
            }
            if (System.getenv("ISSUER").length() == 0) {
                throw new Exception("ISSUER is not provided");
            }

            final Jwk jwk = jwkProvider.get(JWT.decode(token).getKeyId());
            final Algorithm algorithm = Algorithm.RSA256((RSAPublicKey) jwk.getPublicKey(), null);
            final JWTVerifier verifier = JWT.require(algorithm)
                .withAudience(System.getenv("AUDIENCE"))
                .withClaimPresence("roles")
                .withIssuer(System.getenv("ISSUER"))
                .build();

            final DecodedJWT jwt = verifier.verify(token);
            // Since we verify we have the correct Audience we validate the token if at least one role is present, no
            // matter which one.
            final Claim roles = jwt.getClaim("roles");
            if (roles == null || roles.isNull() || roles.asArray(Object.class).length == 0) {
                throw new GuacamoleInvalidCredentialsException(
                    "Token must contain a 'roles' claim", CredentialsInfo.USERNAME_PASSWORD);
            }

            List<String> rolesList = roles.asList(String.class);
            if (rolesList.stream().noneMatch(x -> x.equalsIgnoreCase("WorkspaceOwner")
                || x.equalsIgnoreCase("WorkspaceResearcher"))) {
                throw new GuacamoleInvalidCredentialsException(
                    "User must have a workspace owner or workspace researcher role", CredentialsInfo.USERNAME_PASSWORD);
            }
        } catch (final Exception ex) {
            LOGGER.error("Could not validate token", ex);
            throw new GuacamoleInvalidCredentialsException(
                "Could not validate token:" + ex.getMessage(),
                CredentialsInfo.USERNAME_PASSWORD);
        }
    }
}
