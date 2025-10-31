package org.apache.guacamole.auth.azuretre.user;
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

import org.apache.guacamole.net.auth.AuthenticationProvider;
import org.apache.guacamole.net.auth.Credentials;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.*;

@ExtendWith(MockitoExtension.class)
public class AzureTREAuthenticatedUserTest {

    @Mock
    private Credentials credentialsMock;

    @Mock
    private AuthenticationProvider authProviderMock;

    String dummyAccessToken =
        "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImtnMkxZczJUMENUaklmajRydDZKSXluZW4zOCJ9.eyJhdWQiOiI2ZjY3ZjI3Y"
          + "S04NTk4LTQ4ZGMtYTM1OC00MDVkMzAyOThhMDMiLCJpc3MiOiJodHRwczovL2xvZ2luLm1pY3Jvc29mdG9ubGluZS5jb20vYWY0MTg"
          + "0ZGItNjdhOC00ZDMxLWJjMDYtYmUwN2IwMGJlYWQwL3YyLjAiLCJpYXQiOjE2MDIxNzUxODQsIm5iZiI6MTYwMjE3NTE4NCwiZXhwI"
          + "joxNjAyMTc5MDg0LCJhaW8iOiJBVFFBeS84UkFBQUFRWVRQZW8yM3NpN0ZuQjZXbEtIZUs5MnhFZGN5T3NKWDhzSXBkRUpRd2dnR1g"
          + "3M0ZFL0hPTCtDZU1STjdrQlJoIiwiYXpwIjoiNmY2N2YyN2EtODU5OC00OGRjLWEzNTgtNDA1ZDMwMjk4YTAzIiwiYXpwYWNyIjoiM"
          + "SIsIm5hbWUiOiJNYXJjdXMgVGVzdCIsIm9pZCI6IjYzYTE3NzY0LThiZWEtNDk4Yi1hYzEyLWZjNTRlMzMwMDAxNyIsInByZWZlcnJ"
          + "lZF91c2VybmFtZSI6Im1hcmN1c3Rlc3RAZHJlZGV2Mm91dGxvb2sub25taWNyb3NvZnQuY29tIiwicmgiOiIwLkFBQUEyNFJCcjZob"
          + "k1VMjhCcjRIc0F2cTBIcnlaMi1ZaGR4SW8xaEFYVEFwaWdOMEFITS4iLCJyb2xlcyI6WyJQcm9qZWN0LUFkbWluaXN0cmF0b3IiLCJ"
          + "Qcm9qZWN0LVVzZXIiXSwic2NwIjoiZW1haWwgb3BlbmlkIHByb2ZpbGUgVXNlci5SZWFkIiwic3ViIjoiLUg2aFdjR0pRd2hJVE9Za"
          + "kNJY1RkV2V3UkNfMUZHZXFHZnZpQV91Q0JVRSIsInRpZCI6ImFmNDE4NGRiLTY3YTgtNGQzMS1iYzA2LWJlMDdiMDBiZWFkMCIsInV"
          + "wbiI6Im1hcmN1c3Rlc3RAZHJlZGV2Mm91dGxvb2sub25taWNyb3NvZnQuY29tIiwidXRpIjoiMk1wVHo3WExXVTJzQV9ENVRWaTZBQ"
          + "SIsInZlciI6IjIuMCIsIndpZHMiOlsiYjc5ZmJmNGQtM2VmOS00Njg5LTgxNDMtNzZiMTk0ZTg1NTA5Il19.qG8CZ7_AIxvt7YTy9U"
          + "qhLUujv_fIdwTWrnKZlN9AE5tJvaHCNP_7URJWbE9J3tcH2Ot6pYORHqqhcRAYe6pGP1w4FZFLt-GRLBfZ80V6uuYTIA3BmZEimVBM"
          + "QchPfwpZm6kJhT8Jc9qeMXoZbPVNoeMAf1mFthgQ_VfffGt_tnX-vf9CCsQcS7D175RNpbbpKXvQVoupIt_iwdxhwb6_cJSTolV8P4"
          + "ohJWKcU3dP61wzWuHP50wgxbvDIVqk7ltTTNFG36TAwlzd9-C_sztIoaIKRss_WIhSAu01SY6bWAw75M33KqRZt0KmvQRpwd14yeuG"
          + "K1ulUa8_-t3lynqWfw";

    @Test
    public void authenticatedUserReturnsClaims() {
        final AzureTREAuthenticatedUser authenticatedUser =
            new AzureTREAuthenticatedUser(credentialsMock, dummyAccessToken, "dummy_username", "dummy_objectId", null);

        assertEquals("dummy_objectId", authenticatedUser.getObjectId());
        assertEquals("dummy_username", authenticatedUser.getIdentifier());
        assertEquals(dummyAccessToken, authenticatedUser.getAccessToken());
        assertEquals(credentialsMock, authenticatedUser.getCredentials());
        assertNull(authenticatedUser.getAuthenticationProvider());
    }

    @Test
    public void authenticatedUserWithAuthProvider() {
        final AzureTREAuthenticatedUser authenticatedUser =
            new AzureTREAuthenticatedUser(credentialsMock, dummyAccessToken, "test_user", "test_oid", authProviderMock);

        assertEquals("test_oid", authenticatedUser.getObjectId());
        assertEquals("test_user", authenticatedUser.getIdentifier());
        assertEquals(authProviderMock, authenticatedUser.getAuthenticationProvider());
    }

    @Test
    public void authenticatedUserConvertsUsernameToLowercase() {
        final AzureTREAuthenticatedUser authenticatedUser =
            new AzureTREAuthenticatedUser(credentialsMock, dummyAccessToken, "TEST_USER", "test_oid", null);

        assertEquals("test_user", authenticatedUser.getIdentifier());
    }

    @Test
    public void authenticatedUserWithNullObjectId() {
        final AzureTREAuthenticatedUser authenticatedUser =
            new AzureTREAuthenticatedUser(credentialsMock, dummyAccessToken, "test_user", null, null);

        assertNull(authenticatedUser.getObjectId());
        assertEquals("test_user", authenticatedUser.getIdentifier());
    }

    @Test
    public void authenticatedUserWithEmptyAccessToken() {
        final AzureTREAuthenticatedUser authenticatedUser =
            new AzureTREAuthenticatedUser(credentialsMock, "", "test_user", "test_oid", null);

        assertEquals("", authenticatedUser.getAccessToken());
        assertNotNull(authenticatedUser.getCredentials());
    }

    @Test
    public void authenticatedUserWithLongAccessToken() {
        final String longToken = dummyAccessToken + dummyAccessToken;
        final AzureTREAuthenticatedUser authenticatedUser =
            new AzureTREAuthenticatedUser(credentialsMock, longToken, "test_user", "test_oid", null);

        assertEquals(longToken, authenticatedUser.getAccessToken());
    }

    @Test
    public void authenticatedUserWithSpecialCharactersInUsername() {
        final AzureTREAuthenticatedUser authenticatedUser =
            new AzureTREAuthenticatedUser(credentialsMock, dummyAccessToken, "Test.User@Domain.Com", "test_oid", null);

        assertEquals("test.user@domain.com", authenticatedUser.getIdentifier());
    }

    @Test
    public void authenticatedUserPreservesCredentials() {
        final AzureTREAuthenticatedUser authenticatedUser =
            new AzureTREAuthenticatedUser(credentialsMock, dummyAccessToken, "test_user", "test_oid", authProviderMock);

        assertSame(credentialsMock, authenticatedUser.getCredentials());
    }
}
