HTTP Status Codes — Protea Bakes Backend Reference

A practical reference for the HTTP status codes you will encounter while building and testing the Protea Bakes Django REST API.

1. The Basic Groups

Range

Meaning

Think of it as

1xx

Informational

“The request is being processed.”

2xx

Success

“The request worked.”

3xx

Redirection

“Look somewhere else / use cached information.”

4xx

Client error

“The request is wrong or not allowed.”

5xx

Server error

“The server failed while handling a valid request.”

For your API work, you will mainly use 2xx, 4xx, and occasionally 5xx.

2. Success Codes — 2xx

200 OK

The request succeeded.

Common API uses:

GET /api/products/
GET /api/products/123/
PATCH /api/cart/items/5/

Example:

return Response(data, status=status.HTTP_200_OK)

Remember: “The server successfully did what I asked.”

201 Created

A new resource was successfully created.

Common API uses:

POST /api/cart/items/
POST /api/reviews/
POST /api/payments/initiate/

Example:

return Response(
    data,
    status=status.HTTP_201_CREATED,
)

Remember: “Something new was created.”

202 Accepted

The server accepted the request, but processing has not necessarily finished.

Useful for genuinely asynchronous work.

Example:

POST /api/some-long-running-operation/
→ 202 Accepted

You probably won't use this often in the current Protea Bakes API.

Remember: “I accepted the job; it may finish later.”

204 No Content

The request succeeded, but there is no response body.

Common use:

DELETE /api/cart/items/5/

Example:

return Response(status=status.HTTP_204_NO_CONTENT)

Remember: “It worked, but there is nothing to return.”

3. Client Error Codes — 4xx

These are extremely important for your API tests.

400 Bad Request

The request reached the server, but the data/request is invalid.

Examples:

{
    "rating": 6
}

when the API only accepts ratings from 1–5.

Or:

Invalid promotion code
Invalid product/order combination
Invalid checkout data

Example:

return Response(
    {"detail": "Invalid data."},
    status=status.HTTP_400_BAD_REQUEST,
)

Remember: “You sent something invalid.”

401 Unauthorized

The request requires authentication, but the client has not authenticated successfully.

Example:

GET /api/orders/

without a valid JWT.

In your catalog problem, you saw:

Expected: 200
Actual:   401

That meant the catalog endpoint was requiring authentication when it was supposed to be publicly readable.

Remember: “Who are you?”

Important distinction:

401 is about authentication.

403 Forbidden

The server knows who you are, but you are not allowed to perform the action.

Example:

Customer attempts an admin-only inventory operation.

The user may be authenticated, but lacks the required permission.

Remember: “I know who you are, but you aren't allowed to do that.”

Important distinction:

401 → You aren't authenticated.
403 → You are authenticated, but don't have permission.

404 Not Found

The requested resource cannot be found.

Example:

GET /api/products/999999/

when product 999999 doesn't exist.

It can also happen when the object exists in the database but isn't available through the endpoint's queryset.

This is why your inactive-product test expected:

404

If the public catalog queryset only contains active products, an inactive product effectively isn't available through that endpoint.

Remember: “That resource isn't available at this URL.”

405 Method Not Allowed

The URL exists, but that HTTP method isn't supported there.

Example:

POST /api/products/

when the catalog is read-only.

Your ReadOnlyModelViewSet gives you this behavior.

For example:

GET    /api/products/    → 200
POST   /api/products/    → 405

Remember: “This endpoint exists, but you can't use that HTTP method here.”

406 Not Acceptable

The server cannot provide a response matching the client's requested representation.

This is less common in your normal DRF development.

Remember: “I can't give you the response format you requested.”

409 Conflict

The request conflicts with the current state of the resource.

Examples can include:

Trying to create a duplicate resource
Conflicting state transition
Concurrent modification

You may choose this status code for certain business conflicts, although your current services often use 400 for business-rule failures.

Remember: “Your request conflicts with the current state.”

415 Unsupported Media Type

The server doesn't understand the format of the request body.

Example:

Client sends an unsupported Content-Type.

For JSON APIs you normally send:

Content-Type: application/json

Remember: “I don't understand the format you sent.”

422 Unprocessable Content

The request is syntactically valid, but the data cannot be processed according to the application's rules.

Some APIs use 422 for validation/business-rule errors.

DRF commonly returns 400 for serializer validation errors, so you'll see 400 more often in your project.

Remember: “I understand what you sent, but can't process it.”

429 Too Many Requests

The client has sent too many requests in a given period.

Usually associated with rate limiting.

Example:

1000 requests in a very short period
→ 429 Too Many Requests

Remember: “Slow down.”

4. Server Error Codes — 5xx

These mean the server failed while processing the request.

500 Internal Server Error

An unexpected server-side error occurred.

Example:

Unhandled Python exception
Database error
Programming bug

If your API unexpectedly returns 500, look at the Django traceback.

Remember: “The server broke while handling the request.”

502 Bad Gateway

A server acting as a gateway/proxy received an invalid response from another server.

Common in production infrastructure.

Example:

Nginx → Django → another service

If the upstream service responds incorrectly, a gateway may return 502.

Remember: “The server I contacted got a bad response from another server.”

503 Service Unavailable

The server is temporarily unable to handle the request.

Examples:

Server overloaded
Maintenance
Dependency temporarily unavailable

Remember: “The service is temporarily unavailable.”

504 Gateway Timeout

A gateway/proxy waited too long for another server to respond.

Example:

Nginx → Django

or:

Django → external payment provider

and the upstream response takes too long.

Remember: “The other server took too long.”

5. The Codes You Should Know First

You do not need to memorize every HTTP status code.

For Protea Bakes, make these automatic:

Code

Meaning

Typical Protea Bakes use

200

OK

Successful GET/PATCH

201

Created

Successful POST creating something

204

No Content

Successful DELETE

400

Bad Request

Invalid input/business validation

401

Unauthorized

Not authenticated

403

Forbidden

Authenticated but not permitted

404

Not Found

Resource unavailable/not found

405

Method Not Allowed

Wrong HTTP method

409

Conflict

State/resource conflict

429

Too Many Requests

Rate limiting

500

Internal Server Error

Unexpected backend failure

502

Bad Gateway

Upstream service failure

503

Service Unavailable

Temporary service outage

504

Gateway Timeout

Upstream service timed out

6. Authentication vs Permission

This distinction caused your catalog failure, so remember it:

401 Unauthorized
        ↓
Authentication problem
        ↓
"Who are you?"

versus:

403 Forbidden
        ↓
Permission problem
        ↓
"I know who you are,
but you can't do this."

Example:

GET /api/catalog/

Public endpoint:

Anonymous user → 200

Admin-only endpoint:

Anonymous user → 401
Customer       → 403
Admin          → 200

7. HTTP Method + Status Code

Your API tests frequently combine these concepts.

GET

Usually retrieves something:

GET /api/products/
→ 200

POST

Usually creates something:

POST /api/reviews/
→ 201

PATCH

Usually partially updates something:

PATCH /api/cart/items/5/
→ 200

DELETE

Usually removes something:

DELETE /api/cart/items/5/
→ 204

Unsupported method

POST /api/products/

when the endpoint is read-only:

→ 405

8. A Simple Decision Tree

When an API request fails, ask:

Did the request succeed?
│
├── YES
│   ├── 200 → successful operation
│   ├── 201 → created something
│   └── 204 → successful, no response body
│
└── NO
    │
    ├── 400 → Is my data/request invalid?
    │
    ├── 401 → Am I authenticated?
    │
    ├── 403 → Do I have permission?
    │
    ├── 404 → Does the resource exist/is it available?
    │
    ├── 405 → Am I using the correct HTTP method?
    │
    ├── 409 → Does my request conflict with current state?
    │
    ├── 429 → Am I being rate limited?
    │
    └── 5xx → Something failed on the server/infrastructure

9. DRF Status Constants

In Django REST Framework, prefer the readable constants rather than magic numbers:

from rest_framework import status

Then:

status.HTTP_200_OK
status.HTTP_201_CREATED
status.HTTP_204_NO_CONTENT
status.HTTP_400_BAD_REQUEST
status.HTTP_401_UNAUTHORIZED
status.HTTP_403_FORBIDDEN
status.HTTP_404_NOT_FOUND
status.HTTP_405_METHOD_NOT_ALLOWED
status.HTTP_409_CONFLICT
status.HTTP_429_TOO_MANY_REQUESTS
status.HTTP_500_INTERNAL_SERVER_ERROR

Instead of:

return Response(data, status=200)

use:

return Response(
    data,
    status=status.HTTP_200_OK,
)

It makes the code self-explanatory.

10. The Warning You Saw

You reported:

rest_framework/fields.py:1015: UserWarning:
min_value should be an integer or Decimal instance.

This is not a test failure. It is a Python/DRF warning.

It means somewhere in your serializers you probably have something similar to:

serializers.DecimalField(
    max_digits=10,
    decimal_places=2,
    min_value=0,
)

DRF expects min_value for a DecimalField to be either:

Decimal("0")

or an appropriate integer/Decimal value depending on the field.

The safest fix for a DecimalField is:

from decimal import Decimal

serializers.DecimalField(
    max_digits=10,
    decimal_places=2,
    min_value=Decimal("0"),
)

For example:

from decimal import Decimal
from rest_framework import serializers


class ExampleSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
    )

How to find which app caused it

Run your full test suite with warnings turned into errors:

python -W error manage.py test

The warning will then become an exception and Django will show you the exact serializer/line that triggered it.

Alternatively, search your backend for:

min_value=

Pay particular attention to:

serializers.DecimalField(...)

You already have several decimal fields across the project — orders, payments, promotions, etc. — so the warning could come from any serializer rather than necessarily the app you were working on.

One thing to remember

The model validators and serializer field validators are separate layers.

For example, this model:

models.DecimalField(
    max_digits=10,
    decimal_places=2,
    validators=[MinValueValidator(0)],
)

is not necessarily the source of this warning.

The warning specifically points toward a DRF serializer field, because the warning originates from:

rest_framework/fields.py

So don't change your tested models just because of this warning.
