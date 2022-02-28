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

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.Base64.Encoder;

/**
 * Contains the state data needed to implement Proof Key for Code Exchange
 * (PKCE).
 */
public class CodeChallengeState {
    private static final String CODE_CHALLENGE_METHOD = "S256";
    private final String id;
    private final String codeVerifier;
    private final String codeChallenge;
    private final long expires;

    /**
     * Initializes a new instance of the {@link CodeChallengeState} class.
     *
     * @param maxAge
     */
    public CodeChallengeState(long maxAge) {
        final SecureRandom rng = new SecureRandom();
        final Encoder b64 = Base64.getUrlEncoder().withoutPadding();
        byte[] iddata = new byte[24];
        byte[] randomdata = new byte[32];

        rng.nextBytes(iddata);
        rng.nextBytes(randomdata);

        this.id = b64.encodeToString(iddata);
        this.codeVerifier = b64.encodeToString(randomdata);
        this.codeChallenge = createChallenge(this.codeVerifier);

        this.expires = System.currentTimeMillis() + maxAge;
    }

    public String getId() {
        return this.id;
    }

    /**
     * The code_challenge_method as defined in RFC 7636
     * (https://tools.ietf.org/html/rfc7636)
     *
     * @return "S256"
     */
    public String getChallengeMethod() {
        return CODE_CHALLENGE_METHOD;
    }

    /**
     * The code_verifier as defined in RFC 7636
     * (https://tools.ietf.org/html/rfc7636)
     *
     * @return The randomly generated code_verifier.
     */
    public String getCodeVerifier() {
        return this.codeVerifier;
    }

    /**
     * The code_challenge as defined in RFC 7636
     * (https://tools.ietf.org/html/rfc7636)
     *
     * @return Base64 encoded SHA-256 hash of the code_verifier
     */
    public String getCodeChallenge() {
        return this.codeChallenge;
    }

    /**
     * Has the sate data expired?
     *
     * @return true if the maximum age of the state has not been exceded, otherwise
     *         false.
     */
    public Boolean isStillValid() {
        return this.expires > System.currentTimeMillis();
    }

    /**
     * Generates the code_challenge from the code verifier, as per RFC 7636.
     *
     * @param codeVerifier A 43 character random string.
     * @return BASE64URL-ENCODE(SHA256(ASCII(code_verifier)))
     */
    private static String createChallenge(String codeVerifier) {
        try {
            MessageDigest messageDigest = MessageDigest.getInstance("SHA-256");
            byte[] hash = messageDigest.digest(codeVerifier.getBytes(StandardCharsets.US_ASCII));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(hash);
        } catch (NoSuchAlgorithmException e) {
            return null;
        }
    }
}
