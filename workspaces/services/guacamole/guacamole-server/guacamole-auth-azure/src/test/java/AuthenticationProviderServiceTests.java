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

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThat;
import static org.junit.Assert.fail;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.security.KeyFactory;
import java.security.NoSuchAlgorithmException;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.interfaces.RSAPrivateKey;
import java.security.interfaces.RSAPublicKey;
import java.security.spec.InvalidKeySpecException;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;
import java.util.Calendar;
import java.util.Date;

import com.auth0.jwk.Jwk;
import com.auth0.jwk.JwkException;
import com.auth0.jwk.UrlJwkProvider;
import com.auth0.jwt.JWT;
import com.auth0.jwt.algorithms.Algorithm;

import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.AuthenticationProviderService;
import org.apache.guacamole.auth.azuretre.user.AzureTREAuthenticatedUser;
import org.apache.guacamole.net.auth.Credentials;
import org.apache.guacamole.net.auth.credentials.GuacamoleInvalidCredentialsException;
import org.apache.http.client.ClientProtocolException;
import org.hamcrest.CoreMatchers;
import org.junit.Assert;
import org.junit.Rule;
import org.junit.Test;
import org.junit.contrib.java.lang.system.EnvironmentVariables;
import org.mockito.MockedStatic;
import org.mockito.Mockito;

public class AuthenticationProviderServiceTests {


  private static PublicKey getPublicKey() throws NoSuchAlgorithmException, InvalidKeySpecException {

    // openssl rsa -in private.pem -outform PEM -pubout -out public.pem
    String rsaPublicKey = "-----BEGIN PUBLIC KEY-----"
        + "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtFfaNjrzA2gSHzzXPZnY"
        + "lGCWYuzU8hKJchNqnuSQW+j06Mnp8YTEDp1pP50SQmye1i0hQdE8hb8PC8O7C9NN"
        + "pYbrWoxQRJnhV/mdgfESaWrngsFr6KPVGzUWssEtF1uLHv6Y5SkhXpjHgx6+NKhL"
        + "0iWnsEDg9aj1viTq6VXAsqfsOjGTVjaz/TnSUSzgAjor/7QbUk+6gZUWiU5nq3qJ"
        + "NpF6KRAgfcvOTFO7bN9piUt19gMaPMHW9PGTwXO1SywUMCLnyhTGPVqTm/nW8Tj2"
        + "j+51l6yo1ARFTjdcwstYVIKby0LFeUQEZYfaEFHN78N1ztGSuHuH+sxyEjuWn0J1" + "oQIDAQAB" + "-----END PUBLIC KEY-----";

    rsaPublicKey = rsaPublicKey.replace("-----BEGIN PUBLIC KEY-----", "");
    rsaPublicKey = rsaPublicKey.replace("-----END PUBLIC KEY-----", "");
    X509EncodedKeySpec keySpec = new X509EncodedKeySpec(Base64.getDecoder().decode(rsaPublicKey));
    KeyFactory kf = KeyFactory.getInstance("RSA");
    PublicKey publicKey = kf.generatePublic(keySpec);
    return publicKey;
  }

  private static PrivateKey getPrivateKey() throws NoSuchAlgorithmException, InvalidKeySpecException {

    // openssl genrsa -out private.pem 2048
    // openssl pkcs8 -topk8 -inform PEM -outform DER -in private.pem -out
    // private.der -nocrypt
    String rsaPrivateKey = "-----BEGIN PRIVATE KEY-----"
        + "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC0V9o2OvMDaBIf"
        + "PNc9mdiUYJZi7NTyEolyE2qe5JBb6PToyenxhMQOnWk/nRJCbJ7WLSFB0TyFvw8L"
        + "w7sL002lhutajFBEmeFX+Z2B8RJpaueCwWvoo9UbNRaywS0XW4se/pjlKSFemMeD"
        + "Hr40qEvSJaewQOD1qPW+JOrpVcCyp+w6MZNWNrP9OdJRLOACOiv/tBtST7qBlRaJ"
        + "Tmereok2kXopECB9y85MU7ts32mJS3X2Axo8wdb08ZPBc7VLLBQwIufKFMY9WpOb"
        + "+dbxOPaP7nWXrKjUBEVON1zCy1hUgpvLQsV5RARlh9oQUc3vw3XO0ZK4e4f6zHIS"
        + "O5afQnWhAgMBAAECggEAWhZwuRplftQkCVq5ItqRaD1/olcwYOSFqGiuoEUJIACV"
        + "JxyGMtHhpnNXuiFal7fu+Ip+zIQbOayhdX0HGPcrGH73Xros9rfv66ST2+9zBRoU"
        + "ICtDHmmI8RhqCE2bmsluC8Oe2Qrc0oZ7U7KtzVws1ANfaxpdxhnq+Fs0xe7CXfvQ"
        + "pQ9cu2L0BQ9ilh4ijfekOl/83sdydZ9FkpohIaQEejQhFP9HaMr+RMEcEUbRLERM"
        + "oLzdRsmTDOlKjsJes+LkjxhYzrk6DpBwmyfjI6PYVSzFPgcHY9rqpkXUUoAK5wQf"
        + "KbT40S8cdTaJoALwTgXIRWLjW1zWIe4fmtxs6KCnqQKBgQDuJJ98PoXsZiiIcg9n"
        + "4sSVUHEJB4HpVOih9u9kGxCobQKO+iYkRyyixJci+WIzpD8AMn3IPtgdBGKomTS6"
        + "NwSAIH0Y7JITzsWy9rfUj0L1sB0JEm/uXeeRmxVm+MG5IhBMHMo2LXi8p1v401bn"
        + "2K2NZcqnlA+g+GAvW26n0FIgCwKBgQDB3bT7r8UNh27Qf6mnomPiJOo2+d42ikrv"
        + "U2TZdwGgHfV8psFZ4G4p691OeWDSV4xZ8u1yXjKXV3pbZnO0gxpkFG0dxd0WDllU"
        + "WS8xYewGlx4trOl8Hbtf4RvHJnKM/A+EKx2A6BwPZFDUONTMhywBAHQXPkGSGP0J"
        + "k3CVn+4wgwKBgQCmNb9uawDz3tVZbipceoR0JmHOSIQeg5meOYgZ2V4F/5dyjRsD"
        + "5P09WXKXAXHN00v5akQp99rEXeQyAkQv1+h3OLW3KJ5H3uBTKSli3N6CNfn98/VV"
        + "bAsMsC3+4Y3sFd9EEC/+IjyLh0+E2pRkWvG+p5YK4icKVXBkfS89RwOawwKBgF8i"
        + "zqrocdoWyTG2RGpITZ3voaSC8CJxsR5LHWV+eiS6LvsR1jal5UnbPopBFFuErRKD"
        + "HTUPtuIAAsKRv1wpLi1IvNdsfvdQ6VN0RK2GMU52oE+n2BiZepctn/UWEAbRt0eT"
        + "5PGadhKzltreXMdV2ilPsKirW4A3lQ069nfmuPvDAoGAO0APMgRCFiympXisWEcQ"
        + "Q/U7ZbuYPSBaylBds9GcMoqjlffoxISr20w0iKXokO2DoYmTTeUtjIdfHTt6OIgK"
        + "+KnwY1Wo7yTAtR3Rt1PEPHncSNkRYD7EAIjH7m4EF64awF4ki+34Kfc0/SYxoo2N" + "1A3YhlsQ9cHSWJ2/zjavu/0="
        + "-----END PRIVATE KEY-----";

    rsaPrivateKey = rsaPrivateKey.replace("-----BEGIN PRIVATE KEY-----", "");
    rsaPrivateKey = rsaPrivateKey.replace("-----END PRIVATE KEY-----", "");

    PKCS8EncodedKeySpec keySpec = new PKCS8EncodedKeySpec(Base64.getDecoder().decode(rsaPrivateKey));
    KeyFactory kf = KeyFactory.getInstance("RSA");
    PrivateKey privKey = kf.generatePrivate(keySpec);
    return privKey;
  }

  String audience = "dummy_audience";
  String issuer = "dummy_issuer";

  @Rule
  public final EnvironmentVariables environmentVariables = new EnvironmentVariables();

  private String generateNoRolesJWTToken()
      throws IllegalArgumentException, NoSuchAlgorithmException, InvalidKeySpecException {

    Algorithm algorithm = Algorithm.RSA256((RSAPublicKey) getPublicKey(), (RSAPrivateKey) getPrivateKey());

    Calendar c = Calendar.getInstance();
    Date currentDate = c.getTime();

    c.add(Calendar.HOUR, 24);
    Date expireDate = c.getTime();

    String jwtToken = JWT.create().withIssuer(issuer).withKeyId("dummy_keyid").withAudience(audience)
        .withIssuedAt(currentDate).withExpiresAt(expireDate).withClaim("oid", "dummy_oid")
        .withClaim("preferred_username", "dummy_preferred_username")
        .sign(algorithm);

    return jwtToken;
  }


  private String generateEmptyRolesJWTToken()
      throws IllegalArgumentException, NoSuchAlgorithmException, InvalidKeySpecException {

    Algorithm algorithm = Algorithm.RSA256((RSAPublicKey) getPublicKey(), (RSAPrivateKey) getPrivateKey());

    Calendar c = Calendar.getInstance();
    Date currentDate = c.getTime();

    c.add(Calendar.HOUR, 24);
    Date expireDate = c.getTime();

    String[] emptyUserRoles = { };

    String jwtToken = JWT.create().withIssuer(issuer).withKeyId("dummy_keyid").withAudience(audience)
        .withIssuedAt(currentDate).withExpiresAt(expireDate).withClaim("oid", "dummy_oid")
        .withClaim("preferred_username", "dummy_preferred_username")
        .withArrayClaim("roles", emptyUserRoles)
        .sign(algorithm);

    return jwtToken;
  }

  private String generateValidJWTToken()
      throws IllegalArgumentException, NoSuchAlgorithmException, InvalidKeySpecException {

    Algorithm algorithm = Algorithm.RSA256((RSAPublicKey) getPublicKey(), (RSAPrivateKey) getPrivateKey());

    Calendar c = Calendar.getInstance();
    Date currentDate = c.getTime();

    c.add(Calendar.HOUR, 24);
    Date expireDate = c.getTime();

    String[] validUserRoles = { "Project-User", "Another-Role" };

    String jwtToken = JWT.create().withIssuer(issuer).withKeyId("dummy_keyid").withAudience(audience)
        .withIssuedAt(currentDate).withExpiresAt(expireDate).withClaim("oid", "dummy_oid")
        .withClaim("preferred_username", "dummy_preferred_username").withArrayClaim("roles", validUserRoles)
        .sign(algorithm);

    return jwtToken;
  }

  private String generateExpiredJWTToken()
      throws IllegalArgumentException, NoSuchAlgorithmException, InvalidKeySpecException {

    Algorithm algorithm = Algorithm.RSA256((RSAPublicKey) getPublicKey(), (RSAPrivateKey) getPrivateKey());

    Calendar c = Calendar.getInstance();
    Date currentDate = c.getTime();

    c.add(Calendar.HOUR, -24);
    Date expireDate = c.getTime();

    String[] validUserRole = { "Project-User" };

    String jwtToken = JWT.create().withIssuer(issuer).withKeyId("dummy_keyid").withAudience(audience)
        .withIssuedAt(currentDate).withExpiresAt(expireDate).withClaim("oid", "dummy_oid")
        .withClaim("preferred_username", "dummy_preferred_username").withArrayClaim("roles", validUserRole)
        .sign(algorithm);

    return jwtToken;
  }

  @Test
  public void validateToken_returns_ValidAzureTREAuthenticatedUser()
      throws GuacamoleException, ClientProtocolException, JwkException, IOException, Exception {

    String jwtToken = generateValidJWTToken();
    PublicKey publicKey = getPublicKey();
    Algorithm algorithm = Algorithm.RSA256((RSAPublicKey) publicKey, null);

    try (MockedStatic<Algorithm> mockAlgorithm = Mockito.mockStatic(Algorithm.class)) {

      mockAlgorithm.when(() -> Algorithm.RSA256((RSAPublicKey) publicKey, null)).thenReturn(algorithm);

      Jwk jwk = mock(Jwk.class);
      UrlJwkProvider jwkProvider = mock(UrlJwkProvider.class);
      Credentials credentials = mock(Credentials.class);
      AzureTREAuthenticatedUser authenticatedUser = new AzureTREAuthenticatedUser();

      when(jwk.getPublicKey()).thenReturn((RSAPublicKey) publicKey);
      when(jwkProvider.get("dummy_keyid")).thenReturn(jwk);
      environmentVariables.set("AUDIENCE", audience);
      environmentVariables.set("ISSUER",issuer);

      AuthenticationProviderService azureTREAuthenticationProviderService = new AuthenticationProviderService();
      Method validateToken = AuthenticationProviderService.class.getDeclaredMethod("validateToken", Credentials.class,
          String.class, AzureTREAuthenticatedUser.class, UrlJwkProvider.class);
      validateToken.setAccessible(true);
      validateToken.invoke(azureTREAuthenticationProviderService, credentials, jwtToken, authenticatedUser,
          jwkProvider);

      Assert.assertEquals("dummy_oid", authenticatedUser.getObjectId());
      Assert.assertEquals("dummy_preferred_username", authenticatedUser.getIdentifier());

    }
  }


  @Test
  public void validateToken_throws_when_no_role()
      throws GuacamoleException, ClientProtocolException, JwkException, IOException, Exception {

    String jwtToken = generateNoRolesJWTToken();

    PublicKey publicKey = getPublicKey();
    Algorithm algorithm = Algorithm.RSA256((RSAPublicKey) publicKey, null);

    try (MockedStatic<Algorithm> mockAlgorithm = Mockito.mockStatic(Algorithm.class)) {

      mockAlgorithm.when(() -> Algorithm.RSA256((RSAPublicKey) publicKey, null)).thenReturn(algorithm);

      Jwk jwk = mock(Jwk.class);
      UrlJwkProvider jwkProvider = mock(UrlJwkProvider.class);
      Credentials credentials = mock(Credentials.class);
      AzureTREAuthenticatedUser authenticatedUser = new AzureTREAuthenticatedUser();

      when(jwk.getPublicKey()).thenReturn((RSAPublicKey) publicKey);
      when(jwkProvider.get("dummy_keyid")).thenReturn(jwk);
      environmentVariables.set("AUDIENCE", audience);
      environmentVariables.set("ISSUER", issuer);

      AuthenticationProviderService azureTREAuthenticationProviderService = new AuthenticationProviderService();
      Method validateToken = AuthenticationProviderService.class.getDeclaredMethod("validateToken", Credentials.class,
          String.class, AzureTREAuthenticatedUser.class, UrlJwkProvider.class);
      validateToken.setAccessible(true);

      try {
        validateToken.invoke(azureTREAuthenticationProviderService, credentials, jwtToken, authenticatedUser,
            jwkProvider);
        fail("Exception not thrown");
      } catch (InvocationTargetException e) {
        assertEquals(GuacamoleInvalidCredentialsException.class, e.getTargetException().getClass());
      }
    }
  }


  @Test
  public void validateToken_throws_when_empty_role()
      throws GuacamoleException, ClientProtocolException, JwkException, IOException, Exception {

    String jwtToken = generateEmptyRolesJWTToken();

    PublicKey publicKey = getPublicKey();
    Algorithm algorithm = Algorithm.RSA256((RSAPublicKey) publicKey, null);

    try (MockedStatic<Algorithm> mockAlgorithm = Mockito.mockStatic(Algorithm.class)) {

      mockAlgorithm.when(() -> Algorithm.RSA256((RSAPublicKey) publicKey, null)).thenReturn(algorithm);

      Jwk jwk = mock(Jwk.class);
      UrlJwkProvider jwkProvider = mock(UrlJwkProvider.class);
      Credentials credentials = mock(Credentials.class);
      AzureTREAuthenticatedUser authenticatedUser = new AzureTREAuthenticatedUser();

      when(jwk.getPublicKey()).thenReturn((RSAPublicKey) publicKey);
      when(jwkProvider.get("dummy_keyid")).thenReturn(jwk);
      environmentVariables.set("AUDIENCE", audience);
      environmentVariables.set("ISSUER", issuer);

      AuthenticationProviderService azureTREAuthenticationProviderService = new AuthenticationProviderService();
      Method validateToken = AuthenticationProviderService.class.getDeclaredMethod("validateToken", Credentials.class,
          String.class, AzureTREAuthenticatedUser.class, UrlJwkProvider.class);
      validateToken.setAccessible(true);

      try {
        validateToken.invoke(azureTREAuthenticationProviderService, credentials, jwtToken, authenticatedUser,
            jwkProvider);
        fail("Exception not thrown");
      } catch (InvocationTargetException e) {
        assertEquals(GuacamoleInvalidCredentialsException.class, e.getTargetException().getClass());
      }
    }
  }

  @Test
  public void validateToken_throws_when_expired_token()
      throws GuacamoleException, ClientProtocolException, JwkException, IOException, Exception {

    String jwtToken = generateExpiredJWTToken();

    PublicKey publicKey = getPublicKey();
    Algorithm algorithm = Algorithm.RSA256((RSAPublicKey) publicKey, null);

    try (MockedStatic<Algorithm> mockAlgorithm = Mockito.mockStatic(Algorithm.class)) {

      mockAlgorithm.when(() -> Algorithm.RSA256((RSAPublicKey) publicKey, null)).thenReturn(algorithm);

      Jwk jwk = mock(Jwk.class);
      UrlJwkProvider jwkProvider = mock(UrlJwkProvider.class);
      Credentials credentials = mock(Credentials.class);
      AzureTREAuthenticatedUser authenticatedUser = new AzureTREAuthenticatedUser();

      when(jwk.getPublicKey()).thenReturn((RSAPublicKey) publicKey);
      when(jwkProvider.get("dummy_keyid")).thenReturn(jwk);
      environmentVariables.set("AUDIENCE", audience);
      environmentVariables.set("ISSUER", issuer);
      
      AuthenticationProviderService azureTREAuthenticationProviderService = new AuthenticationProviderService();
      Method validateToken = AuthenticationProviderService.class.getDeclaredMethod("validateToken", Credentials.class,
          String.class, AzureTREAuthenticatedUser.class, UrlJwkProvider.class);
      validateToken.setAccessible(true);

      try {
        validateToken.invoke(azureTREAuthenticationProviderService, credentials, jwtToken, authenticatedUser,
            jwkProvider);
        fail("Exception not thrown");
      } catch (InvocationTargetException e) {
        assertEquals(GuacamoleInvalidCredentialsException.class, e.getTargetException().getClass());
        assertThat(e.getTargetException().getMessage(),CoreMatchers.containsString("The Token has expired on"));
      }

    }
  }
}
