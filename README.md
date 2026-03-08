# rivt

Architectural linting for AI-assisted codebases.

You told Cursor to add an endpoint. It imported the ORM directly in the router. You told it to call a third-party API. It scattered `os.getenv()` across three files and forgot the timeout. The code works. It passes type checks. But it doesn't follow your architecture — and you won't notice until code review.

rivt catches these violations automatically. It checks import boundaries, framework conventions, and code hygiene using static analysis. Error messages are designed to be actionable for both humans and LLMs — an agent can run `rivt check`, read the output, and fix every violation without you looking at the diff.

```
app/routers/users.py:5:0    LNT001  Routers must not import from repositories. Import from services, schemas instead. (found: app.repositories.user)
app/services/order.py:3:0   LNT001  Services must not import fastapi. Raise a domain exception and handle it in the router layer. (found: fastapi.HTTPException)
app/services/email.py:4:14  LNT002  Do not access environment variables directly. Read from the config module instead (app/core/config.py).
app/clients/stripe.py:9:22  LNT005  Add timeout parameter to httpx.Client() (e.g. timeout=10).

Found 4 violations in 3 files.
```

rivt ships with a FastAPI preset and is designed to support any framework over time.

## Install

```
pip install git+https://github.com/AhmedAbbasDeveloper/rivt.git
```

Requires Python 3.11+.

## Quick start

```bash
rivt init    # generate config in pyproject.toml
rivt check   # run checks
```

`rivt init` creates a default configuration. Edit the paths to match your project:

```toml
[tool.rivt]
preset = "fastapi"

[tool.rivt.paths]
routers = "app/routers"
services = "app/services"
repositories = "app/repositories"
clients = "app/clients"
config_module = "app/core/config.py"
schemas = "app/schemas"
models = "app/models"
```

Exit codes: `0` clean, `1` violations found, `2` config error.

## Rules

The FastAPI preset ships with 5 rules:

| Rule   | Name           | What it enforces                                          |
| ------ | -------------- | --------------------------------------------------------- |
| LNT001 | layer-imports  | Import boundaries between architectural layers            |
| LNT002 | no-env-vars    | No `os.getenv()` / `os.environ` outside the config module |
| LNT003 | response-model | Route handlers must declare a response type               |
| LNT004 | status-code    | POST/DELETE handlers must declare `status_code`           |
| LNT005 | http-timeout   | HTTP calls must specify a `timeout`                       |

See [RULES.md](RULES.md) for detailed examples and rationale for each rule.

## Configuration

All configuration lives in `pyproject.toml` under `[tool.rivt]`.

### Preset

The preset defines layer relationships and library restrictions. Currently available: `fastapi`.

```toml
[tool.rivt]
preset = "fastapi"
```

### Paths

Tell rivt where things live in your project:

```toml
[tool.rivt.paths]
routers = "app/routers"
services = "app/services"
repositories = "app/repositories"
clients = "app/clients"
config_module = "app/core/config.py"
schemas = "app/schemas"
models = "app/models"
```

`config_module` is the file where LNT002 allows env var access. `schemas` and `models` enforce that ORM models are only imported by repositories, while schemas are accessible from any layer. Paths can be directories (`app/models`) or single files (`src/models.py`). Remove them if your project doesn't separate these.

### Overrides

Override the default ORM or HTTP client if your stack differs:

```toml
[tool.rivt]
preset = "fastapi"
orm = "sqlmodel"           # default: sqlalchemy
http_client = "requests"   # default: httpx
```

### Disabling rules

```toml
[tool.rivt]
disable = ["LNT004"]
```

### Excluding paths

```toml
[tool.rivt]
exclude = ["tests/**", "migrations/**", "scripts/**"]
```

### Inline suppression

```python
from app.repositories.user import UserRepo  # rivt: disable=LNT001
```

## Adopting in an existing codebase

Running rivt on a large codebase for the first time will surface many violations. That's expected. Adopt progressively:

1. **Start with a few rules.** Disable the ones you're not ready for with `disable = [...]`.
2. **Narrow the scope.** Exclude directories with `exclude = [...]`.
3. **Add to CI.** Enforce on new code immediately.
4. **Clean up over time.** Re-enable rules and remove exclusions as you fix violations.

## Use with AI agents

rivt is built for workflows where agents write most of the code. Add `rivt check` to your feedback loop:

- **Pre-commit hook**: Violations block commits.
- **CI check**: Violations block merges.
- **Agent loop**: The agent runs `rivt check`, reads the output, and fixes violations autonomously.

The error messages tell the agent exactly what's wrong and how to fix it. You stop reviewing structure and focus on whether the code does what you asked.

## Complements, doesn't replace

rivt is not a general-purpose linter. Use it alongside:

- **Ruff** — formatting, style, general Python lint rules
- **Pyright / mypy** — type checking

rivt checks what they don't: architectural boundaries, framework conventions, and codebase-specific rules.
