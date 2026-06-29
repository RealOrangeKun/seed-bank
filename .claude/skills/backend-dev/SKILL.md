---
name: backend-dev
description: Production backend conventions for the seed-bank FastAPI service — software engineering principles (SOLID/DRY/KISS/YAGNI), the layered architecture, async DB, structured logging, error handling, anti-patterns to refuse, and review checklists. Use whenever you write or modify code under src/seedbank/.
---

# Backend dev — production conventions

## Scope

How we build backend code under `src/seedbank/`. Read this before you write or
modify a module there; the `backend-engineer` subagent reviews against the same
rules, so reading it first saves a review round-trip.

The skill has three parts: **software engineering principles** (apply to any
codebase, any language), **anti-patterns** (named smells and their fixes), and
**seed-bank patterns** (the FastAPI/SQLAlchemy/async stack). Don't skip the
first part — most review feedback traces back to it.

The voice throughout is rule-plus-rationale: the rule tells you what we do, the
*why* tells you when it applies and when a deviation is defensible. A rule you
understand is one you can apply to a case it didn't anticipate.

---

# Part 1 — Software engineering principles

Code that violates these tends to be hard to change safely, even when it
"works" today. Each principle below pairs the rule with what it buys you.

## SOLID

**S — Single Responsibility.** A class, function, or module has one
reason to change. If you describe what a thing does and use the word
"and" twice, split it.
- *In this repo:* `services/auth_service.py` issues tokens. It does NOT also send email — that's a notification service. It does NOT also rotate secrets — that's a worker task.
- Tell-tale sign of violation: the file has imports from three unrelated subsystems.

**O — Open/Closed.** A module is open for extension, closed for
modification. New behavior comes from adding code, not editing
unrelated code.
- *In this repo:* the ML registry is the canonical example. Adding a new model = drop a new builder file with `@register_builder("...")`. Zero edits to `manager.py`, `services/`, or `api/`.
- If you find yourself editing an `if/elif` chain to add a case, you're violating OCP. Replace with a registry, dispatch table, or polymorphism.

**L — Liskov Substitution.** A subtype must be usable wherever its
supertype is. If `B` extends `A` but breaks `A`'s contract, you have
inheritance abuse.
- *In this repo:* every `InferenceBackend` (`torch_local`, `roboflow`, `ultralytics_yolo`) must satisfy the same Protocol — same input shape, same output shape, same exception types on failure. A backend that throws a different exception class for the same condition violates LSP.

**I — Interface Segregation.** Clients shouldn't depend on methods they
don't use. Many small interfaces beat one fat one.
- *In this repo:* a router that needs only `get_user_by_id` should depend on a Protocol with that one method, not on the full `UserRepository` class. Small interfaces also make tests trivially mockable.

**D — Dependency Inversion.** High-level modules depend on
abstractions, not concretions. Concretions are injected.
- *In this repo:* services receive `Repository`, `ObjectStorage`,
  `InferenceBackend` instances via constructor. Never `from
  infrastructure.db.session import SessionLocal` inside a service —
  that imports a concretion.

## DRY — Don't Repeat Yourself

Duplicated logic is two bugs waiting to be fixed in one place.
- Knowledge duplicated > typing duplicated. Two functions that *look*
  similar may serve different purposes — don't merge them.
- The right time to extract is the **third** occurrence, not the second.
  Two similar lines might be coincidence; three is a pattern.
- Copy-paste with a small tweak is the #1 source of subtle bugs.
  When you `Ctrl-D` a block, stop and ask: should this be a function?

**Don't apply DRY across layers.** A response schema and a domain
entity may have similar fields — that's not duplication, that's a
boundary. Conflating them creates leaky abstractions.

## KISS — Keep It Simple

The goal is the simplest code that solves the problem cleanly.
- Prefer a function to a class until state demands a class.
- Prefer a class to a metaclass. Always.
- Prefer composition to inheritance. Inheritance is for "is-a"; composition is for "has-a."
- Three lines of similar code beat a clever 1-line abstraction nobody else can read.
- If you have to write a comment to explain *what* the code does (not
  *why*), the code is too clever. Rewrite the code.

## YAGNI — You Aren't Gonna Need It

Don't build for hypothetical future requirements.
- No "configurable" options with one possible value.
- No abstract base class with one implementation.
- No plugin system unless there's a second plugin coming this quarter.
- No `# TODO: support X later` left as scaffolding. Either build X now
  or leave the simple form.

YAGNI is **not** an excuse to skip security, observability, or error
handling. Those are needs of every system, not future needs.

## Separation of concerns

Each layer of the stack handles exactly one kind of concern. Mixing
concerns is the most common cause of unmaintainable code.

| Concern | Layer |
|---|---|
| HTTP parsing, status codes, content negotiation | `api/` |
| Authentication, authorization | `api/deps.py` (dependency-injected into routers) |
| Business rules, transactions, orchestration | `services/` |
| Persistence queries | `infrastructure/db/repositories/` |
| Domain invariants, value objects | `domain/` |
| Cross-cutting (logging, metrics, config) | `core/` |

Symptoms of mixed concerns:
- A router doing `await session.execute(...)` (HTTP layer touching SQL).
- A service importing `fastapi.Request` (business logic depending on the framework).
- A repository checking permissions (data layer making business decisions).

## Composition over inheritance

Inheritance is the most overused tool in the OO toolbox.
- Use inheritance when there's a genuine "is-a" relationship in the
  domain (rare).
- Use composition (and Protocols / dataclasses) for "has-a" or "can-do."
- Mixins are inheritance with extra steps. Avoid.

## Tell, Don't Ask + Law of Demeter

- Tell objects what to do; don't ask them for their state and decide
  for them. `user.can_create_widget()` beats `if user.role == "admin" and user.is_active and not user.deleted_at: ...` sprinkled across callers.
- Law of Demeter: don't reach through more than one dot of indirection.
  `batch.user.account.email` is a code smell — the caller knows too much.

## Boundary discipline

- **At the edges**, validate aggressively. HTTP request → Pydantic with
  field constraints. External API response → re-validate the shape.
- **At the core**, trust your types. A domain entity that already exists
  has already passed validation. Don't re-check.
- **Errors at boundaries are recoverable.** Errors at the core are bugs.
  Treat them differently — recoverable errors get a domain exception
  that maps to HTTP; bugs get logged with full traceback and propagate.

## Function and class size

- A function over **30 lines** of body needs a reason. Over **50** is
  almost always wrong.
- A class with more than **7 public methods** probably violates SRP.
  Look for two cohesive groupings inside it.
- Cyclomatic complexity > 10 means too many branches. Extract or
  flatten with early returns.
- **Avoid more than 3 levels of nesting.** Use early returns, guard
  clauses, and extracted helpers.

## Naming

- Names reveal intent. `process_data` is not a name; it's a placeholder.
- Booleans read as questions: `is_active`, `has_admin_role`, `can_publish`.
- Avoid encodings: no Hungarian (`strName`), no type prefixes (`I`Repository).
- Long descriptive names beat short cryptic ones — your IDE autocompletes either.
- A function's name + signature should let a reader skip its body 90% of the time.

## Comments

- Comment **why**, not **what**. The code says what.
- A comment that contradicts the code is worse than no comment. Update both.
- `# TODO` without a ticket reference and an owner is a lie. Either
  remove it or commit to fixing it.
- Docstrings on public functions/classes; no fluff on internals that
  the type signature already explains.

## Immutability and pure functions

- Prefer immutable values. `frozen=True` on dataclasses unless mutation is essential.
- Pure functions (no side effects, deterministic given inputs) are easier to test and reason about. Push side effects to the edges.
- A function that takes a list, mutates it in place, AND returns it is the worst of both worlds. Pick one.

## Errors

- Errors are values to be handled, not exceptions to swallow.
- Specific exception classes > generic. Catch `NotFoundError`, not `Exception`.
- Re-raise with context: `raise ConflictError(...) from e` preserves the chain.
- **Never use exceptions for control flow** of expected outcomes
  (e.g., "user not found" is a normal outcome of a search; return
  `None` or an `Optional[...]`).

## Logging

- Log events, not free-form prose. Structured `event="user.login", user_id=...` beats `f"user {x} logged in"`.
- Log levels mean something: `DEBUG` developer-only, `INFO` significant business event, `WARNING` something unusual but recoverable, `ERROR` something failed and we couldn't recover.
- **Never log secrets, tokens, full JWTs, passwords, OAuth codes, or full presigned URLs.**
- Don't log inside hot loops at INFO level. Aggregate and log once.

---

# Part 2 — Anti-patterns

A non-exhaustive catalog of named smells, each with the reason it hurts and the
fix. Spotting one in a diff is a reason to ask for a change before merge —
naming the smell makes the feedback concrete instead of a matter of taste.

## Architectural anti-patterns

### God file / God object
A single file or class that does many unrelated things. The legacy
`main.py` (1,642 lines containing routing + ML + DB + I/O) is the
canonical example.
- **Smell:** the file imports from > 5 unrelated subsystems.
- **Fix:** split by responsibility, not by line count.

### Big ball of mud
No discernible architecture; everything imports everything.
- **Smell:** circular imports, "where does this logic live?" has no clear answer.
- **Fix:** the layered architecture in `CLAUDE.md`. Imports flow downward only.

### Anemic domain model
Data classes with no behavior; all logic lives in services.
- **Smell:** services are thousands of lines, entities are bags of getters/setters.
- **Fix:** push invariants into the entity. `User.activate()` belongs on `User`, not in `auth_service`.

### Leaky abstraction
A higher layer leaks details of the layer below.
- **Smell:** a router catching `sqlalchemy.exc.IntegrityError`.
- **Fix:** the repository converts driver exceptions to domain exceptions; the router never sees the driver.

### Lava flow
Old, possibly-dead code preserved "just in case."
- **Smell:** `# old version, kept for reference` blocks; commented-out functions.
- **Fix:** delete it. Git remembers.

### Golden hammer
Using one tool/pattern for every problem.
- **Smell:** every async problem solved with a Celery task; every persistence problem solved with raw SQL.
- **Fix:** match the tool to the problem.

### Premature abstraction
Generalizing for needs that don't exist.
- **Smell:** an abstract base class with one concrete subclass.
- **Fix:** inline the abstraction. Re-introduce it when the second use case actually arrives (and shapes it correctly, which it couldn't before).

### Premature optimization
Complicating code for performance gains you can't measure.
- **Smell:** in-memory cache, custom hash table, "fast" code path with no benchmark.
- **Fix:** profile first. Optimize the actual bottleneck.

## Code-level anti-patterns

### Magic numbers / Magic strings
Unnamed literals scattered through code.
- **Smell:** `if status == 1:`, `Path("/uploads")`.
- **Fix:** named constants in `core/config.py` or a domain enum.

### Primitive obsession
Using primitives where a value object would do.
- **Smell:** passing `email: str` everywhere, validating it in 7 places, getting it wrong in 2 of them.
- **Fix:** an `Email` value object with validation in its constructor.

### Stringly-typed APIs
Using strings where an enum, type, or value object would be safer.
- **Smell:** `status: str` on a model with no CHECK constraint.
- **Fix:** `Enum` + DB CHECK constraint.

### Boolean parameter
Functions with a boolean flag that fundamentally changes behavior.
- **Smell:** `def fetch(user_id, active_only: bool)`.
- **Fix:** two functions: `fetch_active(user_id)` and `fetch_all(user_id)`. Or pass an enum.

### Data clumps
The same group of parameters appearing together everywhere.
- **Smell:** `def f(start_date, end_date, timezone, format): ...` repeated.
- **Fix:** a `DateRange` value object.

### Long parameter list
A function with > 4 positional parameters.
- **Fix:** keyword-only arguments after the first 1–2; or group into a value object / dataclass.

### Feature envy
A method that uses another object's data more than its own.
- **Smell:** `service.do_thing(user)` does five `user.x = ...` operations.
- **Fix:** move the method to `User`.

### Shotgun surgery
A single conceptual change requires editing 10 files.
- **Smell:** adding a field requires changes to ORM + repo + service + schema + router + tests + docs (some of those are necessary; if you're editing more than that for a *field rename*, the design is wrong).
- **Fix:** centralize the concept. Often a sign of duplicated knowledge.

### Copy-paste programming
Same logic in multiple places.
- **Smell:** a bug fix needed in the same shape in 4 functions.
- **Fix:** extract on the third occurrence (see DRY above).

### Hardcoded credentials / config
Secrets or environment-specific values in source.
- **Smell:** `API_KEY = "vBZaHEYnhnXfg0StVnqV"` (this is a real example from the legacy repo).
- **Fix:** `Settings(BaseSettings)` reading from env. Pre-commit hook with a secret scanner.

### Bare except
`except:` or `except Exception:` with no re-raise.
- **Smell:** silent failures, debugging nightmares.
- **Fix:** catch the specific class. Re-raise as a domain exception. Log with `exc_info=True` if you must swallow.

### Returning None to mean error
Conflating "no result" with "error."
- **Smell:** `return None` on both "user not found" and "DB unreachable."
- **Fix:** raise on errors; return `None` only for legitimate "no result" cases.

### Catching exceptions to ignore them
`except SomeError: pass`
- **Fix:** if you don't care, log at DEBUG. If you really don't care, comment why.

### Mutable default arguments
`def f(x=[]): ...` — Python's most famous foot-gun.
- **Fix:** `def f(x=None): x = x or []`.

### Singleton / Global mutable state
Shared mutable state that anyone can read or write.
- **Smell:** `MODEL_MANAGER = None; def init(): global MODEL_MANAGER; ...`
- **Fix:** dependency injection. The container or app factory holds the instance; consumers receive it.

### Spaghetti exception flow
Using exceptions for normal control flow.
- **Smell:** `try: cache.get(...) except KeyError: ...` instead of `cache.get(..., default=None)`.
- **Fix:** explicit checks for expected outcomes.

### Type punning / `Any` proliferation
Lazy `Any` annotations defeat the type system.
- **Smell:** `def handler(payload: Any) -> Any: ...`
- **Fix:** type it properly. If you genuinely don't know, use `object` and narrow with `isinstance`.

---

# Part 3 — Seed-bank specific patterns

This is the FastAPI/SQLAlchemy/async-stack cookbook. The principles in
Part 1 still apply on top.

## Layered architecture

```
api/v1/<feature>.py        ← FastAPI router. Parses request, calls service, returns schema.
services/<feature>.py      ← Use case orchestration. Domain rules. No FastAPI.
infrastructure/db/repositories/<feature>.py  ← SQLAlchemy queries. No business logic.
domain/<entity>.py         ← Plain dataclass entities. No framework imports.
schemas/<feature>.py       ← Pydantic v2 request/response DTOs.
```

Imports flow downward only:
- `api → services → infrastructure`
- `services → domain`
- `schemas` is imported only by `api` (and by tests).

## How to add an endpoint

See the dedicated `add-endpoint` skill for the full step-by-step. The
seven files are: domain entity, ORM model, repository, service,
schemas, router, tests. Skipping any one means somebody else fixes it
after merge.

## Async DB patterns

```python
# infrastructure/db/repositories/widget.py
class WidgetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, widget_id: UUID) -> Widget | None:
        stmt = select(WidgetORM).where(WidgetORM.id == widget_id)
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_by_owner(
        self, owner_id: UUID, *, limit: int, offset: int
    ) -> list[Widget]:
        stmt = (
            select(WidgetORM)
            .where(
                WidgetORM.owner_id == owner_id,
                WidgetORM.deleted_at.is_(None),
            )
            .order_by(WidgetORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]
```

Rules:
- `session` is provided per-request via FastAPI dependency; the router doesn't manage transactions, **the service does** (`async with session.begin(): ...`).
- Never call `session.commit()` in a repository — that's the service's job.
- Eager-load relationships you actually use with `selectinload(...)`. Never trigger an N+1 by accessing a relationship in a loop.
- Repositories return **domain entities**, not ORM objects. ORM types stop at the repository boundary.

## Pydantic schemas

```python
# schemas/widget.py
from seedbank.schemas.common import STRICT_INPUT

class WidgetCreate(BaseModel):
    model_config = STRICT_INPUT  # the shared ConfigDict(extra="forbid")
    name: Annotated[str, Field(min_length=1, max_length=120)]
    description: Annotated[str, Field(max_length=2000)] = ""

class WidgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    created_at: datetime
```

- Use the shared `STRICT_INPUT` from `schemas/common.py` on every input schema
  rather than redeclaring `ConfigDict(extra="forbid")` — one definition means
  the policy can't drift field by field. `extra="forbid"` rejects unknown keys
  at the edge, which catches client typos and blocks unexpected fields from
  sneaking through.
- Length / range limits on every string and number.
- No raw `dict[str, Any]` in responses unless the field is genuinely free-form metadata, in which case constrain its top-level shape.
- Never reuse one schema for input and output. Different concerns, different validation, different fields.
- **Wrap every response.** Single resources → `Envelope[XOut]` (`{"data": ...}`); paginated collections → `Page[XOut]` (`{"data": [...], "meta": {page, page_size, total, has_more}}`); small bounded segments (e.g. traffic splits for one `(kind, seed_type_id)`) → `Envelope[list[XOut]]`. The generics live in `schemas/common.py` along with the `paginate(...)` helper. `/healthz`, `/readyz`, and `/metrics` are the **only** documented exemptions — Kubernetes and Prometheus expect raw shapes there.

## Errors

The `DomainError` hierarchy in `core/exceptions.py` is the full set; raise the
one that fits rather than inventing a new class casually:

```python
# core/exceptions.py
class DomainError(Exception):
    """Base for application-level errors that map to HTTP responses.

    Each subclass carries a stable `code` and a human `title` as class
    attributes — that is what api/errors.py renders into the response.
    """

class NotFoundError(DomainError): ...        # -> 404
class ConflictError(DomainError): ...         # -> 409
class ValidationError(DomainError): ...       # -> 422 (domain-level, not Pydantic's)
class AuthError(DomainError): ...             # -> 401
class ForbiddenError(DomainError): ...        # -> 403
class RateLimitError(DomainError): ...        # -> 429
class ExternalServiceError(DomainError): ...  # -> 502/503 (MinIO, MLflow, etc.)
class ModelNotReadyError(DomainError): ...    # -> 503 (no production model loaded)
```

- **Services raise these; they never `raise HTTPException(...)`.** Keeping HTTP
  out of the service layer is what lets the same service back a CLI, a worker,
  or a test without dragging FastAPI along.
- `api/errors.py` maps each domain error to an **RFC 9457 Problem Details**
  response (`application/problem+json`). The body carries the standard
  `type` / `title` / `status` / `detail` / `instance` plus our extensions:
  `code` (the machine-readable enum, e.g. `forbidden`, `not_found`,
  `validation_error`), `request_id` (for correlation), and `errors[]` (per-field
  on 422).
- `code` and `title` come from the exception class — set them as class
  attributes on any new `DomainError` subclass. Clients branch on `code`, so
  changing an existing one is a breaking change; treat it like an API version
  bump.
- Routers `raise HTTPException(...)` only for genuine protocol-level issues
  (e.g. a malformed `Range` header), never for domain reasons — a domain reason
  has a `DomainError` for it.

## Logging

```python
import structlog
log = structlog.get_logger()

await svc.create_widget(...)
log.info("widget.created", widget_id=str(widget.id), owner_id=str(user.id))
```

- Event names are `noun.verb` lower case.
- Pass UUIDs as strings (avoid implicit JSON serialization issues).
- `request_id` and `user_id` are auto-bound by middleware — don't pass them through every call.
- Never use f-strings for log messages. The whole point of structlog is searchable structured fields.

## Config

```python
# core/config.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SEEDBANK_")
    widget_max_per_user: int = Field(default=100, ge=1)
```

- All env reads go through `Settings`. Never `os.environ[...]` outside `core/config.py`.
- Every new setting ships with a default (or a clear "required") and a matching `.env.example` entry.
- `get_settings()` is `@lru_cache`-d — call it freely.

## Concurrency rules

- The request handler runs on the event loop. **Anything that blocks the loop blocks all other requests.**
- CPU-heavy work (model inference, image processing) → Celery worker, not the API.
- Sync libraries (e.g. some PIL operations) → `await asyncio.to_thread(...)` if they must run in-process and are short.
- File I/O → `aiofiles` or move to `asyncio.to_thread`. Never `open(huge_file).read()` in a handler.
- Outbound HTTP → `httpx.AsyncClient` with explicit timeout. Never `requests`.

## Transactions

- A service method is the unit of business work, so it owns the transaction.
- `async with self.session.begin(): ...` brackets the work. Within the block, repositories `add` / `flush` but don't commit.
- A failure mid-transaction rolls back automatically.
- Don't open nested transactions casually. If you genuinely need savepoints, document why.

## Quick smells reviewers flag (cheat sheet)

Each line below maps to a rule above; the parenthetical is why it matters.

- `@router.get("/...")` followed by `db.execute(...)` — router is touching the ORM.
- `from fastapi import HTTPException` inside `services/` — service depending on the framework.
- `f"SELECT ... WHERE id = {x}"` — SQL injection.
- `except Exception:` with no re-raise — silent failure.
- `requests.get(...)` — sync HTTP in an async path.
- Reading `os.environ["X"]` outside `core/config.py`.
- A new `analyze` endpoint variant — extend the unified one instead.
- A new `if seed_type == "...":` branch — use the registry.
- A `print()` statement — use structlog.
- A literal string longer than 60 chars hardcoded outside a constant or config.
- Adding a column without an index when it's used in a WHERE clause.

---

# Review checklist (paste into PRs touching `src/seedbank/`)

- [ ] No new file > 400 lines (excluding generated migrations)
- [ ] No function > 50 lines of body
- [ ] No class with > 7 public methods (or split is justified in a comment)
- [ ] Every public function has a type annotation; no `Any` without a comment
- [ ] No layering violations (router → ORM, service → FastAPI, etc.)
- [ ] No bare `except`
- [ ] No `print` or f-string logs
- [ ] No hardcoded credentials, paths, or thresholds
- [ ] Every new env var is in `Settings` and `.env.example`
- [ ] Every new endpoint has request schema + response schema + at least 1 unit + 1 integration + 1 e2e test
- [ ] Negative tests exist (401/403/404/422/409 as applicable)
- [ ] Migration round-trips (up → down → up)
- [ ] Coverage on new code is high on `services/` and `domain/` (target ≥ 95%),
      ≥ 80% overall — the enforced CI floor is temporarily relaxed (see the
      `testing` skill), so don't let touched modules regress in the meantime
