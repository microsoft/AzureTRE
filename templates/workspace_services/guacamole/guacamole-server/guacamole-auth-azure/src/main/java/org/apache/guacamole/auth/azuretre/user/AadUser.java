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

package org.apache.guacamole.auth.azuretre.user;

import java.util.HashMap;
import java.util.Map;

import com.nimbusds.jwt.JWT;
import com.nimbusds.jwt.JWTClaimsSet;
import java.text.ParseException;

import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.net.auth.AbstractUser;
import org.apache.guacamole.net.auth.User;
import org.apache.guacamole.language.TranslatableMessage;
import org.apache.guacamole.language.TranslatableGuacamoleClientException;

public class AadUser extends AbstractUser {
    private Map<String, String> attributes = new HashMap<>();

    /**
     * Creates a completely uninitialized SimpleUser.
     */
    public AadUser() {
    }

    /**
     * Creates a new AadUser with properties from the OIDC Id token.
     *
     * @param idToken
     *     The identity token from the OIDC flow.
     * @throws GuacamoleException
     */
    public AadUser(JWT idToken) throws GuacamoleException {

        try {
            JWTClaimsSet claims = idToken.getJWTClaimsSet();

            super.setIdentifier((String)claims.getClaim("oid"));

            // Set full name attribute
            attributes.put(User.Attribute.FULL_NAME, claims.getStringClaim("name"));

            // Set email address attribute (needs to be configured in AAD)
            String email = claims.getStringClaim("email");
            if (email != null) {
                attributes.put(User.Attribute.EMAIL_ADDRESS, email);
            }

            super.setAttributes(attributes);
        }
        catch (ParseException exception)
        {
            throw new TranslatableGuacamoleClientException("Error parsing the id token.", new TranslatableMessage("LOGIN.ID_TOKEN_ERROR"));
        }
    }

    @Override
    public Map<String, String> getAttributes() {
        return this.attributes;
    }
}
