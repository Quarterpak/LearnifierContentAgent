---
source: https://www.learnifier.com/api
language: en
---

Learnifier is the easiest way to start creating courses, and with our API, you have the opportunity as a developer to connect Learnifier with other services that you are using.

Our Admin API is here to help you integrate with your web site, CRM system, LMS or any others system that you are using. We have the ambition to create an API that is easy to use while still being able to utilize your others systems at their full capacity.

The API is a RESTful API, with predictable resource-oriented URLs. The API uses standard HTTP verbs like GET, POST, PUT and DELETE. You can use any standard HTTP client to talk to the API.

**All IDs are strings**All unique identifiers in the API are case sensitive strings and consist of alphanumeric characters.

**All timestamps are UTC**Timestamps returned by the API are in the UTC timezone and in ISO8601 format.

**All requests must be over HTTPS**Requests to the API must be made using HTTPS. Please remember to have your client validate SSL certificates.

**All data must be encoded as UTF-8**Please encode all data using UTF-8. We will always return UTF-8 encoded responses.

**All data must be valid JSON**We expect all data to be valid JSON, and will return HTTP error 400 Bad Request otherwise.

**Always set the required headers**As we only support JSON data, the API expects the Content-Type header to be set to application/json.

Building our API is an ongoing effort, and we rely on your feedback for what to focus on next. If you don’t see a resource you want here, please let us know!

This is the authentication procedure for Learnifier REST API. The system is using HTTP Basic authentication.

The authentication is based on a pair of keys called: key and secret. Another term for key is username and the alternative term for secret is password.

The “key” will be (clearly) exchanged between the systems, while the “secret” will be used to create the concatenated parameter. The call will be executed as described, and the Authorization parameter must be added to its header as follows:

Authorization: Basic <code>The code value is simply the “key” and “secret” concatenated with a colon (‘:’) in between.

This is an example of encoding in pseudo-code:$code = $key + ‘:’ + $secret; request.sendHeaderLine( ‘Authorization: Basic ‘ + base64($code) )

or example, if the key is *Aladdin *as the secret is *open sesame*, then the field’s value is the Base64 encoding of *Aladdin:open sesame*, or *QWxhZGRpbjpvcGVuIHNlc2FtZQ==*. Then the *Authorization* header field will appear as:

Authorization: Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==

There was a previous authentication method using an X-Authentication header. It was a modified form of the HTTP Basic authentication method and is now deprecated.

Read on a larger desktop screen size to see the swagger interface

Ready to experience Learnifier? Start your free trial or book a personalized demo today!