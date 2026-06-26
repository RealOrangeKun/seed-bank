---
name: add-endpoint
description: Step-by-step recipe for adding a new HTTP endpoint or feature module to the seed-bank API in the layered architecture. Use this when implementing a new resource or bolting a new operation onto an existing one.
---

# Add an HTTP endpoint

## Purpose

Add an endpoint that fits the layered architecture cleanly:
`router → service → repository → ORM`, with Pydantic at the boundary. A
correct new aggregate touches **seven** files; each one carries a single
concern, so skipping one means another layer absorbs work that isn't its job
and the next reader can't predict where logic lives.

## When to use

Implementing a new resource (its own table and lifecycle) or adding an
operation to an existing one. Reach for `/scaffold-feature <name>` first — it
writes the router, service, repository, schemas, and test stubs in the right
places; this skill is the recipe for filling them in.

## Steps

### 0. URL design — get the shape right before writing code

URLs are a public contract; changing one later breaks every client. Decide the
shape now, not in review.

- **Resources are nouns; HTTP methods are the verbs.** `/models`, `/batches`,
  `/api-keys` — never `/get-models` or `/create-widget`. The method
  (`POST`/`GET`/`PATCH`/`DELETE`) carries the action, which keeps the surface
  predictable across features.
- **Plural collections, kebab-case.** `/api-keys`, not `/apikey`. Sub-resources
  nest: `/batches/{id}/detections`.
- **Identifiers in the path**, as UUIDv7. Never expose internal numeric ids.
- **Don't split single-vs-batch endpoints without a real reason.** A real
  reason is a different auth/rate-limit policy, a different latency profile
  (sync vs async), or different idempotency semantics — convenience is not one.
  Prefer one endpoint that accepts a single object **or** an array.
  - *Right:* `POST /analyze` takes one image or a list; there is no
    `/analyze-batch`.
  - *Right:* `/users/me` is separate from `/users/{id}` only because the auth
    model differs (no admin scope). That's a real reason — see `api/v1/users.py`.
  - *Wrong:* `/widgets/bulk-create` when `POST /widgets` could accept a list.
- **Action endpoints are the documented exception.** Auth/RPC steps
  (`/auth/login`, `/auth/refresh`) are protocol moves, not CRUD; keep them
  under `/auth/...`. If you're tempted by `/widgets/{id}/promote`, you're
  probably modeling the resource wrong — a `PATCH` on a status field usually
  fits better (this is exactly how model promotion works).
- **Filter, sort, paginate via query params:** `?status=staging&page=2&page_size=50`.

### Decide first

- New aggregate (own table, own lifecycle) or a new operation on an existing
  one? New aggregate → all seven steps. New operation → steps 4–7, reusing the
  existing repo / domain / model.
- Who can call it? (`end_user`, `ai_developer`, `admin`, public.) This picks
  the dependency on the router.
- User-scoped (filtered by `user_id`)? If so, ownership filtering lives in the
  **repository**, never the router — that keeps the access rule in one place
  instead of scattered across every handler.

### 1. Domain entity (new aggregate)

`src/seedbank/domain/widget.py` — a plain dataclass, no framework imports, so
the domain stays free of FastAPI / SQLAlchemy / Pydantic:

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass(slots=True)
class Widget:
    id: UUID
    owner_id: UUID
    name: str
    description: str
    created_at: datetime
    deleted_at: datetime | None
```

### 2. SQLAlchemy ORM

Append to `src/seedbank/infrastructure/db/models.py`. PK via `uuid7()` (not
`uuid4` — sortable, index-friendly); FK carries `ondelete="CASCADE"`:

```python
class WidgetORM(Base):
    __tablename__ = "widgets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(2000), default="")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)

    __table_args__ = (Index("ix_widgets_owner_created", "owner_id", "created_at"),)
```

Generate the migration with `/new-migration "add widget table"` and review it
per the `db-migration` skill.

### 3. Repository

`src/seedbank/infrastructure/db/repositories/widget.py` — SQLAlchemy queries,
no business logic, returning **domain entities** (ORM types stop here):

```python
class WidgetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, widget: Widget) -> Widget:
        self.session.add(WidgetORM(id=widget.id, owner_id=widget.owner_id, ...))
        await self.session.flush()
        return widget

    async def get_for_owner(self, widget_id: UUID, owner_id: UUID) -> Widget | None:
        stmt = select(WidgetORM).where(
            WidgetORM.id == widget_id,
            WidgetORM.owner_id == owner_id,
            WidgetORM.deleted_at.is_(None),
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_for_owner(self, owner_id: UUID, *, limit: int, offset: int) -> list[Widget]: ...
    async def count_for_owner(self, owner_id: UUID) -> int: ...
```

Ownership filtering and the soft-delete predicate both live here — one place
that owns "which rows this owner may see."

### 4. Service

`src/seedbank/services/widget_service.py` — orchestration and domain rules; it
owns the transaction and raises `core.exceptions.*`, never `HTTPException` (a
service that imported FastAPI would couple business logic to the framework):

```python
class WidgetService:
    def __init__(self, *, repo: WidgetRepository, settings: Settings) -> None:
        self.repo = repo
        self.settings = settings

    async def create(self, *, owner_id: UUID, payload: WidgetCreatePayload) -> Widget:
        if await self.repo.count_for_owner(owner_id) >= self.settings.widget_max_per_user:
            raise ConflictError("widget quota exceeded")
        widget = Widget(
            id=uuid7(), owner_id=owner_id, name=payload.name,
            description=payload.description,
            created_at=datetime.now(timezone.utc), deleted_at=None,
        )
        async with self.repo.session.begin():  # the service brackets the unit of work
            return await self.repo.add(widget)

    async def get(self, *, owner_id: UUID, widget_id: UUID) -> Widget:
        w = await self.repo.get_for_owner(widget_id, owner_id)
        if w is None:
            raise NotFoundError(f"widget {widget_id}")
        return w
```

### 5. Schemas (DTOs)

`src/seedbank/schemas/widget.py`. Reference the shared input config rather than
redeclaring `extra="forbid"` everywhere, and keep input and output schemas
separate — they validate different things and drift apart over time:

```python
from seedbank.schemas.common import STRICT_INPUT

class WidgetCreate(BaseModel):
    model_config = STRICT_INPUT  # extra="forbid": reject unknown fields at the edge
    name: Annotated[str, Field(min_length=1, max_length=120)]
    description: Annotated[str, Field(max_length=2000)] = ""

class WidgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    owner_id: UUID
    name: str
    description: str
    created_at: datetime
```

**Don't write your own list/page shape.** The cross-cutting wrappers live in
[`schemas/common.py`](../../../src/seedbank/schemas/common.py) so every client
sees one stable envelope:

- `Envelope[T]` — single-resource wrapper, `{"data": T}`.
- `Page[T]` — paginated collection, `{"data": [T], "meta": PageMeta}` where
  `PageMeta` is `{page, page_size, total, has_more}`.
- `paginate(items, *, total, page, page_size)` — builds the `Page`.

Only `/healthz`, `/readyz`, and `/metrics` are exempt — Kubernetes and
Prometheus expect raw shapes there; everything else wraps. Errors are RFC 9457
Problem Details emitted by `api/errors.py` from the `DomainError` you raise.

### 6. Router

`src/seedbank/api/v1/widgets.py` — parse, call the service, return a schema.
Routers never import SQLAlchemy. (`api/v1/users.py` is a good thin-router
reference.)

```python
from seedbank.schemas.common import Envelope, Page, paginate

router = APIRouter(prefix="/widgets", tags=["widgets"])

@router.post("", response_model=Envelope[WidgetRead], status_code=201)
async def create_widget(
    payload: WidgetCreate,
    user: AuthenticatedUser = Depends(current_user),
    svc: WidgetService = Depends(get_widget_service),
) -> Envelope[WidgetRead]:
    widget = await svc.create(owner_id=user.id, payload=payload)
    return Envelope[WidgetRead](data=WidgetRead.model_validate(widget))

@router.get("", response_model=Page[WidgetRead])
async def list_widgets(
    user: AuthenticatedUser = Depends(current_user),
    svc: WidgetService = Depends(get_widget_service),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[WidgetRead]:
    rows, total = await svc.list(owner_id=user.id, limit=page_size, offset=(page - 1) * page_size)
    items = [WidgetRead.model_validate(r) for r in rows]
    return paginate(items, total=total, page=page, page_size=page_size)
```

Pagination is `?page=&page_size=` (1-indexed, max 200). The service returns
`(rows, total)`; the router does the offset arithmetic and calls `paginate`.

Wire it up in `api/v1/__init__.py` (`api_v1.include_router(widgets.router)`)
and add the DI factory in `api/deps.py`:

```python
def get_widget_repo(session: AsyncSession = Depends(get_db)) -> WidgetRepository:
    return WidgetRepository(session)

def get_widget_service(
    repo: WidgetRepository = Depends(get_widget_repo),
    settings: Settings = Depends(get_settings),
) -> WidgetService:
    return WidgetService(repo=repo, settings=settings)
```

### 7. Tests

Three files (templates in the `testing` skill), one per pyramid layer so a
failure points at the layer that broke:

- `tests/unit/services/test_widget_service.py` — service with a mocked repo.
  Cover happy path, quota exceeded, not-found.
- `tests/integration/db/test_widget_repository.py` — repo against the
  testcontainer Postgres. Cover the ownership filter and the soft-delete filter.
- `tests/e2e/test_widgets.py` — full HTTP flow. Cover 201, 401, 404, 422, 409.

Asserting on responses:

- Success: unwrap the envelope — `body = r.json()["data"]` for a single
  resource; for a collection `r.json()["data"]` is the list and
  `r.json()["meta"]` carries `page`/`page_size`/`total`/`has_more`.
- Errors: assert `Content-Type` starts with `application/problem+json`,
  `body["status"]` is the expected code, and `body["code"]` is the
  machine-readable enum (`"forbidden"`, `"not_found"`, `"validation_error"`).
  `tests/integration/test_envelopes.py` has the canonical `_assert_problem_shape`.

## Conventions

- Imports flow downward only: `api → services → infrastructure`;
  `services → domain`; `schemas` is imported by `api` and tests.
- Service owns the transaction; the repository never commits.
- Every response wraps in `Envelope`/`Page` except the three probe routes.
- Log structured events at the service boundary: `log.info("widget.created", widget_id=..., owner_id=...)`.

## Gotchas

- A router doing `await session.execute(...)` is a layering violation — that
  query belongs in the repository.
- Reusing one schema for input and output couples request validation to
  response shape; keep them separate.
- Forgetting the `extra="forbid"` (`STRICT_INPUT`) config lets typo'd fields
  pass silently instead of 422-ing at the edge.

## Checklist

- [ ] All seven files exist and are wired up (router included, DI factory added)
- [ ] `make check` passes
- [ ] `make test` passes
- [ ] `.env.example` updated if you added a setting
- [ ] OpenAPI docs at `/api/v1/docs` show the endpoint with the right schema
- [ ] No literal credentials, no `print()`, no bare `except`
- [ ] Structured events logged (`widget.created`, etc.)
