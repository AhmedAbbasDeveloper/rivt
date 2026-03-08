# Rules

## LNT001 — layer-imports

Enforces import boundaries between architectural layers.

Each layer has two constraints:

1. **Layer-to-layer**: A layer can only import from the layers its preset allows.
2. **Library restrictions**: Framework, ORM, and HTTP client libraries are restricted to their respective layers.

The FastAPI preset enforces:

| Layer        | Can import from                | Allowed restricted libraries |
| ------------ | ------------------------------ | ---------------------------- |
| routers      | services, schemas              | fastapi                      |
| services     | repositories, clients, schemas | (none)                       |
| repositories | schemas, models                | sqlalchemy                   |
| clients      | schemas                        | httpx                        |
| schemas      | (none)                         | (none)                       |
| models       | (none)                         | sqlalchemy                   |

The `schemas` and `models` layers are optional — they only activate if you configure paths for them. When configured, `models` (ORM definitions) can only be imported by repositories, while `schemas` (Pydantic DTOs) are accessible from any layer. Layer paths can be directories (`app/models`) or single files (`src/models.py`).

Files not inside any configured layer are not checked by this rule.

### Layer-to-layer violation

```python
# app/routers/users.py
from app.repositories.user import get_user_by_id

@router.get("/users/{user_id}")
def get_user(user_id: int):
    return get_user_by_id(user_id)
```

```
app/routers/users.py:2:0  LNT001  Routers must not import from repositories. Import from a service instead. (found: app.repositories.user)
```

Correct:

```python
# app/routers/users.py
from app.services.user import get_user

@router.get("/users/{user_id}")
def get_user_route(user_id: int):
    return get_user(user_id)
```

### Library restriction violation

```python
# app/services/order.py
from fastapi import HTTPException

def cancel_order(order_id: int):
    order = get_order(order_id)
    if order.status == "shipped":
        raise HTTPException(status_code=400, detail="Cannot cancel shipped order")
```

```
app/services/order.py:2:0  LNT001  Services must not import fastapi. Raise a domain exception and handle it in the router layer. (found: fastapi.HTTPException)
```

Correct:

```python
# app/services/order.py
from app.exceptions import OrderCancelError

def cancel_order(order_id: int):
    order = get_order(order_id)
    if order.status == "shipped":
        raise OrderCancelError("Cannot cancel shipped order")
```

### Edge cases

- Relative imports are resolved against the file's location and checked the same way. `from ..repositories.user import X` in a router file is a violation.
- Star imports (`from app.repositories import *`) are checked by their source module.

---

## LNT002 — no-env-vars

`os.environ`, `os.getenv()`, and `os.environ.get()` must not be used outside the configured config module.

```python
# app/services/email.py
import os

def send_email(to: str, body: str):
    api_key = os.getenv("SENDGRID_API_KEY")
```

```
app/services/email.py:4:14  LNT002  Do not access environment variables directly. Read from the config module instead (app/core/config.py).
```

Correct:

```python
# app/services/email.py
from app.core.config import settings

def send_email(to: str, body: str):
    api_key = settings.sendgrid_api_key
```

---

## LNT003 — response-model

FastAPI route handlers must declare their response type — either via `response_model` in the decorator or a return type annotation on the function.

Both of these are valid:

```python
@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    return user_service.get(user_id)
```

```python
@router.get("/users/{user_id}")
def get_user(user_id: int) -> UserResponse:
    return user_service.get(user_id)
```

Violation — neither is present:

```python
@router.get("/users/{user_id}")
def get_user(user_id: int):
    return user_service.get(user_id)
```

```
app/routers/users.py:2:0  LNT003  Add response_model to the @router.get() decorator or a return type annotation (e.g. -> UserResponse).
```

---

## LNT004 — status-code

FastAPI route handlers for POST and DELETE must declare an explicit `status_code`.

GET, PUT, and PATCH handlers are excluded — the implicit 200 is almost always correct for reads and updates, and requiring `status_code=200` would be noise. POST and DELETE are the methods where the status code is a real design decision: 201 vs 200 for POST, 204 vs 200 for DELETE.

Violation:

```python
@router.post("/users", response_model=UserResponse)
def create_user(data: CreateUserRequest):
    return user_service.create(data)
```

```
app/routers/users.py:2:0  LNT004  Add status_code to the @router.post() decorator (e.g. status_code=201).
```

Correct:

```python
@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(data: CreateUserRequest):
    return user_service.create(data)
```

DELETE example:

```python
@router.delete("/users/{user_id}")
def delete_user(user_id: int):
    user_service.delete(user_id)
```

```
app/routers/users.py:2:0  LNT004  Add status_code to the @router.delete() decorator (e.g. status_code=204).
```

Correct:

```python
@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    user_service.delete(user_id)
```

---

## LNT005 — http-timeout

Outbound HTTP calls must specify a `timeout` parameter. Missing timeouts can cause cascading failures in production when a downstream service is slow or unresponsive.

This rule checks two patterns:

**1. Direct module-level calls** — `httpx.get()`, `httpx.post()`, etc.

```python
response = httpx.get("https://api.stripe.com/v1/charges")
```

```
app/clients/stripe.py:1:11  LNT005  Add timeout parameter to httpx.get() (e.g. timeout=10).
```

Correct:

```python
response = httpx.get("https://api.stripe.com/v1/charges", timeout=10)
```

**2. Client construction** — `httpx.Client()` and `httpx.AsyncClient()` without timeout.

```python
client = httpx.Client()
```

```
app/clients/stripe.py:1:9  LNT005  Add timeout parameter to httpx.Client() (e.g. timeout=10).
```

Correct:

```python
client = httpx.Client(timeout=10)
```

Method calls on client instances (`client.get(...)`) are not flagged — the timeout is expected to be set on the client constructor.
