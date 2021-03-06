Pithos separate view domain
^^^^^^^^^^^^^^^^^^^^^^^^^^^

This document describes how the Pithos view accesses the protected Pithos
resources and proposes a new design for granting access to specific resources.
It sketches implementation details and configuration concerns.


Abstract
========

We want to serve untrusted user content in a domain which does not have access
to sensitive information. Therefore, we would like the Pithos view to be
deployed in a domain outside the Astakos cookie domain.

We propose a design for the Pithos view to grant access to the
access-restricted resource without consulting the cookie.

Briefly, the Pithos view will request a short-term access token for a specific
resource from Astakos. Before requesting the access token, the view should
obtain an authorization grant (authorization code) from Astakos, which will be
presented by the view during the request for the access token.

The proposed scheme follows the guidelines of the OAuth 2.0 authentication
framework as described in http://tools.ietf.org/html/rfc6749/.


Current state and shortcomings
==============================

Until now, Pithos, in order to identify the user who requests to view a Pithos
resource, uses the information stored by Astakos in the cookie after a
successful user authentication login.

The main drawback of this design is that the Pithos view which serves untrusted
user content has access to the sensitive information stored in the Astakos
cookie.


Proposed changes
================

We propose to alter the Pithos view to obtain authorization according to the
authorization code grant flow.

The general flow comprises the following steps:

#. The user requests to view the content of a protected resource.
#. The view requests an authorization code from Astakos by providing its
   identifier, the requested scope, and a redirection URI.
#. Astakos authenticates the user and validates that the redirection URI
   matches with the registered redirect URIs of the view.
   Once the Pithos view is considered a trusted client, Astakos grants the
   access request on behalf of the user.
#. Astakos redirects the user-agent back to the view using the redirection URI
   provided earlier. The redirection URI includes an authorisation code.
#. The view requests an access token from Astakos by including the
   authorisation code in the request. The view also posts its client identifier
   and its client secret in order to authenticate itself with Astakos. It also
   supplies the redirection URI used to obtain the authorisation code for
   verification.
#. Astakos authenticates the view, validates the authorization code, and ensures
   that the redirection URI received matches the URI used to redirect the
   client. If valid, Astakos responds back with a short-term access token.
#. The view exchanges with Astakos the access token for the information of the
   user to whom the authoritativeness was granted.
#. The view responds with the resource contents if the user has access to the
   specific resource.


Implementation details
======================

Pithos view registration to Astakos
-----------------------------------

The Pithos view has to authenticate itself with Astakos since the latter has to
prevent serving requests by unknown/unauthorized clients.

Each OAuth client is identified by a client identifier (``client_id``).
Moreover, the confidential clients are authenticated via a password
(``client_secret``).  Then, each client has to declare at least one redirect
URI, so that Astakos will be able to validate the redirect URI provided during
the authorization code request. If a client is trusted (like the Pithos view),
Astakos grants access on behalf of the resource owner, otherwise the resource
owner has to be asked.

We register an OAuth 2.0 client with the following command::

    snf-manage oauth2-client-add <client_id> --secret=<secret> --is-trusted --url <redirect_uri>

For example::

    snf-manage oauth2-client-add pithos-view --secret=12345 --is-trusted --url https://node2.example.com/pithos/ui/view

Configure view credentials in Pithos
------------------------------------

We set the credentials used by the Pithos view to authenticate itself
with Astakos during the resource access token generation procedure, in the
``PITHOS_OAUTH2_CLIENT_CREDENTIALS`` setting.

The value should be a ``(<client_id>, <client_secret>)`` tuple.

For example::

    PITHOS_OAUTH2_CLIENT_CREDENTIALS = ("pithos-view", 12345)

Authorization code request
--------------------------

The view receives a request without either an access token or an authorization
code. In that case it redirects to Astakos' authorization endpoint by adding
the following parameters to the query component using the
``application/x-www-form-urlencoded`` format:

::

    response_type:
        'code'
    client_id:
        'pithos-view'
    redirect_uri:
        the absolute path of the view request
    scope:
        the user specific part of the view request path

For example, the client directs the user-agent to make the following HTTP
request using TLS (with extra line breaks for display purposes only)::

    GET /astakos/oauth2/auth?response_type=code&client_id=pithos-view
        &redirect_uri=https%3A//node2.example.com/pithos/ui/view/b0ee4760-9451-4b9a-85f0-605c48bebbdd/pithos/image.png
        &scope=/b0ee4760-9451-4b9a-85f0-605c48bebbdd/pithos/image.png HTTP/1.1
        Host: accounts.synnefo.live

Access token request
--------------------

Astakos' authorization endpoint responses to a valid authorization code
request by redirecting the user-agent back to the requested view
(``redirect_uri`` parameter).

The view receives the request which includes the authorization code and
makes a POST request to the Astakos' token endpoint by sending the following
parameters using the ``application/x-www-form-urlencoded`` format in the HTTP
request entity-body:

::

    grant_type:
        "authorization_code"
    code:
        the authorization code received from the Astakos.
    redirect_uri:
        the "redirect_uri" parameter was included in the authorization request

Since the Pithos view is registered as a confidential client it MUST
authenticate with Astakos by providing an Authorization header including the
encoded client credentials as described in
http://tools.ietf.org/html/rfc2617#page-11.

For example, the view makes the following HTTP request using TLS (with extra
line breaks for display purposes only)::


     POST /astakos/oauth2/token HTTP/1.1
     Host: accounts.synnefo.live
     Authorization: Basic cGl0aG9zLXZpZXc6MTIzNDU=
     Content-Type: application/x-www-form-urlencoded

     grant_type=authorization_code&code=SplxlOBeZQQYbYS6WxSbIA
     &redirect_uri=https%3A//node2.example.com/pithos/ui/view/b0ee4760-9451-4b9a-85f0-605c48bebbdd/pithos/image.png

Access to the protected resource
--------------------------------

Astakos' token endpoint replies to a valid token request with a `200 OK`
response::

     HTTP/1.1 200 OK
     Content-Type: application/json;charset=UTF-8
     Cache-Control: no-store
     Pragma: no-cache

     {
       "access_token":"2YotnFZFEjr1zCsicMWpAA",
       "token_type":"Bearer",
       "expires_in":20
     }

The view redirects the user-agent to itself by adding to the query component
the access token.

The view receives the request which includes an access token and requests
from Astakos to validate the token by making a GET HTTP request to the
Astakos' validation endpoint::

    GET /astakos/identity/v2.0/tokens/2YotnFZFEjr1zCsicMWpAA?belongsTo=/b0ee4760-9451-4b9a-85f0-605c48bebbdd/pithos/image.png HTTP/1.1
    Host: accounts.synnefo.live

The Astakos' validation endpoint checks whether the token is valid, has not
expired and that the ``belongsTo`` parameter matches with the ``scope``
parameter that was included in the token request. If not valid returns a `404
NOT FOUND` response. If valid, returns the information of the user to whom the
token was assigned.

In the former case the view redirects to the requested path (without the access
token or the authorization code) in order to re-initiate the procedure by
requesting an new authorization code.

In the latter case, the view proceeds with the request and if the user has
access to the requested resource the resource's data are returned, otherwise
the access to the resource is forbidden.

Authorization code and access token invalidation
------------------------------------------------

Authorization codes can be used only once (they are deleted after a successful
token creation)

Token expiration can be set by changing the ``OAUTH2_TOKEN_EXPIRES`` setting.
By default it is set to 20 seconds.

Tokens granted to a user are deleted after user logout or authentication token
renewal.

Expired tokens presented to the validation endpoint are also deleted.

Authorization code and access token length
------------------------------------------

Authorization code length is adjustable by the
``OAUTH2_AUTHORIZATION_CODE_LENGTH`` setting. By default it is set to 60
characters.

Token length is adjustable by the ``OAUTH2_TOKEN_LENGTH`` setting. By default
it is set to 30 characters.

Restrict file serving endpoints to a specific host
--------------------------------------------------

A new setting ``PITHOS_UNSAFE_DOMAIN`` has been introduced. When set, all API
views that serve Pithos file contents will be restricted to be served only
under the domain specified in the setting value.

If an invalid host is identified and request HTTP method is one of ``GET``,
``HEAD``, the server will redirect using a clone of the request with host
replaced to the one the restriction applies to.
