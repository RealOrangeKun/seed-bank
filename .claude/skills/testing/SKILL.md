---
name: testing
description: Industry-standard testing principles (FIRST, AAA, one-behavior-per-test, the test pyramid) plus the seed-bank pytest + testcontainers + factory_boy cookbook. Use when adding tests, picking the right layer, debugging flakiness, or auditing coverage.
---

# Testing — principles + cookbook

A test suite is a contract with the future. Bad tests rot faster than
production code because nobody trusts them enough to maintain them. Part 1 is
universal; Part 2 is how we apply it in this repo.

---

# Part 1 — Industry-standard testing principles

## The FIRST principles

**F — Fast.** Unit tests run in milliseconds, integration tests in seconds. If
`pytest tests/unit` takes more than a few seconds, the inner loop is broken and
people stop running tests — which is when bugs slip through.

**I — Independent / Isolated.** A test passes when run alone, in any order, in
parallel, in a fresh worker. "This test depends on test X running first" is a
bug, because the runner is free to reorder or shard.

**R — Repeatable.** Same result every run, on every machine, at every time of
day. No real clock, no real network without a fake, no randomness without a
seed.

**S — Self-validating.** A test asserts; it does not print and ask a human to
read the output. Pass or fail, nothing in between.

**T — Timely.** Tests are written close to the code they test — ideally before,
never "after merge" when the design is already frozen.

## AAA — Arrange, Act, Assert

Three sections, in order, blank lines between. The structure makes the intent
scannable: setup, the one action under test, the outcome.

```python
async def test_widget_create_increments_user_count(db_session):
    # Arrange
    user = await UserFactory.create_async(session=db_session)
    repo = WidgetRepository(db_session)

    # Act
    await repo.add(WidgetFactory.build(owner_id=user.id))

    # Assert
    assert await repo.count_for_owner(user.id) == 1
```

A fourth section ("...and also assert this other thing") means two tests. Split
it. Given/When/Then is the same idea in BDD vocabulary — pick one and keep it
consistent.

## One behavior per test

A test asserts one *logical concept* — not one `assert` line. Several asserts
that all verify the same behavior are fine; asserts that verify two different
behaviors are two tests. When one test fails, the name and the failing assert
should tell you exactly what broke; a test asserting six things hides five
failures behind the first.

## Test naming

Format: `test_<unit>_<scenario>_<expected_behavior>`. A reader should know
what's tested without opening the file.

- `test_register_rejects_duplicate_email` ✅
- `test_login_returns_401_for_unverified_account` ✅
- `test_widget` ❌ (what about it?) / `test_create_widget_works` ❌ ("works" says nothing)

## Test the behavior, not the implementation

Tests should fail when behavior changes, not when an internal refactor happens.
Assert on observable outcomes — HTTP response, DB state, returned value, a
side-effect on a fake. Don't assert that a private helper was called N times,
and don't assert on log contents (logs are observability, not contract). If a
behavior-preserving refactor breaks 30 tests, those tests were testing the
wrong thing.

## The test pyramid

```
        /\        E2E          few, slow, high-confidence
       /  \
      /----\     Integration   some
     /      \
    /--------\  Unit           many, fast
```

Wide at the bottom, narrow at the top. The inverted cone (lots of e2e, few
unit) means slow CI, flaky tests, and poor failure-mode locality.

| Layer | Time budget | Covers |
|---|---|---|
| Unit | < 100 ms each | Pure logic, branches, validation, error paths |
| Integration | < 5 s each | A repo against real Postgres; storage against real MinIO |
| E2E | < 30 s each | A full HTTP flow: auth → endpoint → DB → response |
| Load | minutes | Throughput, latency under concurrency |

Rule of thumb: ~5 integration and ~30 unit tests per e2e test for the same
area. If you're adding e2e tests because unit tests "don't catch enough," the
unit tests are at the wrong granularity.

## Boundary testing & equivalence partitioning

For each input domain, test one representative per valid class, the boundaries
(min, min-1, max, max+1), and one invalid representative. For a
`widget_max_per_user=100` quota: 0 allowed, 99 allowed (last success), 100
rejected. Bugs live at the boundary, not at "10 widgets."

## Negative tests are mandatory

Every endpoint, every service method that can fail, every repository that
filters needs at least one failure-path test. Minimum HTTP set: happy path,
401 unauthenticated, 403 forbidden, 404 missing, 409 conflict (if applicable),
422 validation. Skipping them is how production discovers them.

## Test data — builders > literals

Use a factory, not positional literals. `UserFactory.build(role=Role.ADMIN)`
states what matters and lets defaults fill the rest;
`User(uuid7(), "x@y.com", None, ...)` is brittle the moment a field is added.
The factory is the single place that knows which fields a valid instance needs.

## Determinism

Eliminate every source of nondeterminism: inject a `Clock` or use `freezegun`
for time; seed randomness; use `factory.Sequence` for predictable ids; never
rely on dict/set/row order without `ORDER BY`; fake the network; use `tmp_path`
for the filesystem.

## Don't sleep — wait, with a bound

For genuine async propagation (CDC, queue, eventual consistency), use bounded
retries via `tenacity` or a polling loop with a hard timeout. Never
`asyncio.sleep(5)` and hope — that's slow when it works and flaky when it
doesn't.

## Mocking — the rules

- **Mock at the architectural seam, not inside it.** Mock the repository when
  testing a service. Don't mock `AsyncSession` — that couples the test to
  SQLAlchemy internals and proves nothing about real SQL.
- **Don't mock what you don't own** unless you wrap it first.
- **Fakes > mocks > stubs.** A fake that behaves like the real thing
  (in-memory repo, faked Redis) catches more bugs than a hardcoded return.
- **Mocking five layers deep** means you're at the wrong test level — move up
  to integration or e2e.

## Test smells (catalog)

| Smell | Description | Fix |
|---|---|---|
| Assertion roulette | Many unrelated asserts; can't tell which broke | One behavior per test |
| Mystery guest | Depends on data it doesn't reference | Make setup explicit via fixtures/factories |
| Eager test | Exercises many features at once | Decompose |
| The Giant | Hundreds of lines in one test | AAA each concern into its own test |
| The Flaky | "Rerun fixes it" | Find the nondeterminism; never `@flaky` |
| Over-specified mocks | Asserts the exact internal call sequence | Assert outcomes, not call patterns |
| Inappropriate intimacy | Reaches into private attrs to set up state | Use the public API |

## Coverage — necessary, not sufficient

100% coverage means every line ran, not that every line was tested — a test
with no assertions still covers what it touches. Treat coverage as a floor, not
a goal. Mutation testing (`mutmut`) is the real measure: a suite that catches
no introduced bug despite high coverage is a weak suite. Never game coverage
with no-op tests — false confidence is worse than none.

## What NOT to test

Framework code (FastAPI's request parsing), third-party libraries (SQLAlchemy
works), trivial getters/setters, config files, generated code (migrations,
OpenAPI clients). Test the behavior you build on top of these, not the
dependency itself.

---

# Part 2 — Seed-bank cookbook

## Layout

```
tests/
  conftest.py          # session-scoped containers: postgres, clickhouse; faked redis; minio
  factories/           # factory_boy: UserFactory, BatchFactory, DetectionFactory, ModelArtifactFactory
  unit/                # services with mocked repos; pure logic; no I/O
  integration/         # repos against real Postgres; storage; CDC
  e2e/                 # full HTTP flows via httpx.AsyncClient
  load/                # locust scenarios
```

## Infrastructure under test (current)

- **Postgres** and **ClickHouse** run as real testcontainers (Postgres
  `16-alpine`, ClickHouse `24.10-alpine`). Integration tests hit them directly.
- **Redis** is **faked** (`memory://`), not a container — the broker and cache
  paths exercise an in-memory double, which keeps the suite fast and hermetic.
- **MinIO** is exercised through its real client in integration tests; don't
  mock it.
- **Celery** runs with `task_always_eager` in tests, so a dispatched task runs
  inline and you assert on its effect rather than polling a worker.
- E2E auth: bootstrap the admin via `POST /auth/bootstrap-admin`, then derive
  the other role tokens from there.

## Pyramid policy (per feature)

| Layer | Covers | Never does |
|---|---|---|
| Unit | Service branches, domain validation | Touch DB, Redis, MinIO, ClickHouse, real models |
| Integration | Repo queries, MinIO put/get, ClickHouse insert, Alembic up→down→up | Hit FastAPI; mock anything that has a container |
| E2E | Auth → presign → upload → analyze → fetch result; RBAC denials | Mock the database |
| Load | Steady-state throughput + p95 under concurrency | Run in CI by default |

## Hard rules

1. **Don't mock `AsyncSession`, the MinIO client, or the ClickHouse client.**
   If a test needs them, it's integration or e2e, not unit. (Redis is the one
   double we accept, via the in-memory fake.)
2. **Use `factory_boy` for fixtures** — no raw `User(email=...)` in tests.
3. **One behavior per test.**
4. **Negative tests are mandatory** — every endpoint gets an auth-failure and a
   validation-failure test.
5. **Async tests use `pytest-asyncio`** with `asyncio_mode = "auto"`.
6. **Containers are session-scoped.** Reset state by truncating tables in a
   function-scoped fixture, not by tearing down the container.
7. **Golden-image regression** for analyze: a frozen sample produces detection
   JSON stable within tolerance (bbox coords via `pytest.approx`, counts exact).
8. **No `@pytest.mark.flaky`.** Flakiness is a design bug — fix it, or
   `@pytest.mark.skip` with a tracking issue.

## Known xfails / quirks (don't "fix" these blindly)

- **The 4 DWH dual-write tests are `xfail` (#51)** — root cause in
  [the 4 DWH tests xfail](../../memory/known-issues.md#the-4-dwh-tests-xfail-51). They're expected to fail; an unexpected *pass*
  (`xpass`) means the upstream issue resolved, so remove the marker. Don't paper
  over it by mocking ClickHouse.

## Templates

### Unit (service)

```python
async def test_create_widget_rejects_when_quota_exceeded():
    # Arrange
    repo = AsyncMock(spec=WidgetRepository)
    repo.count_for_owner.return_value = 100
    svc = WidgetService(repo=repo, settings=Settings(widget_max_per_user=100))

    # Act + Assert
    with pytest.raises(ConflictError):
        await svc.create(owner_id=uuid7(), payload=WidgetCreatePayload(name="x"))
    repo.add.assert_not_awaited()
```

### Integration (repository)

```python
async def test_widget_repo_excludes_soft_deleted_rows(db_session):
    # Arrange
    owner = await UserFactory.create_async(session=db_session)
    live = await WidgetFactory.create_async(session=db_session, owner_id=owner.id)
    await WidgetFactory.create_async(
        session=db_session, owner_id=owner.id, deleted_at=datetime.now(UTC)
    )
    repo = WidgetRepository(db_session)

    # Act
    rows = await repo.list_for_owner(owner.id, limit=10, offset=0)

    # Assert
    assert [w.id for w in rows] == [live.id]
```

### E2E (endpoint)

```python
async def test_create_widget_returns_201_with_body(client, end_user_token):
    r = await client.post(
        "/api/v1/widgets",
        headers={"Authorization": f"Bearer {end_user_token}"},
        json={"name": "alpha", "description": "test"},
    )
    assert r.status_code == 201
    body = r.json()["data"]              # responses are Envelope-wrapped
    assert body["name"] == "alpha"
    assert UUID(body["id"])

async def test_create_widget_rejects_anonymous(client):
    r = await client.post("/api/v1/widgets", json={"name": "alpha"})
    assert r.status_code == 401

async def test_create_widget_validates_name_length(client, end_user_token):
    r = await client.post(
        "/api/v1/widgets",
        headers={"Authorization": f"Bearer {end_user_token}"},
        json={"name": ""},
    )
    assert r.status_code == 422
```

Error bodies are RFC 9457 Problem Details — assert
`Content-Type: application/problem+json`, `body["status"]`, and `body["code"]`.

## Coverage policy (current state)

The target is **80% overall**, with `domain/` and `services/` much higher
(≥ 95% — they're the logic integration tests can't reach). The CI coverage gate
is **temporarily relaxed** — measured, not enforced; see [CI gates](../../memory/workflow.md#ci-gates).
Fill the worker / ML / storage / OAuth holes and ratchet the floor back toward
80, and don't let new code drag the measured number down meanwhile.

- `api/` is covered through e2e — don't unit-test routers (that tests FastAPI).
- `infrastructure/` is covered through integration — don't unit-test repos with
  mocked sessions.

## Running the suite

CI mirrors `make`: it installs with `uv sync --frozen --extra dev` (the lockfile
is authoritative — a drifted `uv.lock` fails the gate; see [CI gates](../../memory/workflow.md#ci-gates)),
then runs the pyramid. Locally:

```bash
make test                       # full pyramid
make test-unit                  # fast gate, no full-suite coverage threshold
make test-integration           # testcontainers
pytest tests/e2e -q             # full app
pytest -k "widget" -q           # focused
pytest --cov=seedbank --cov-report=term-missing
```

## When a test is flaky

1. **Stop and read it.** Don't `@flaky`, don't `time.sleep`.
2. Look for: real time, real randomness, race conditions, fixture order,
   container cold start, cross-test state leaks.
3. For genuine eventual consistency (CDC), use `tenacity` with a bounded
   timeout.
4. If still flaky after investigation, it's a system design bug, not a test
   bug. File an issue, `@pytest.mark.skip(reason="<issue link>")`, fix the
   system.

## Checklist

- [ ] Every new service method has unit tests for happy path, expected failure, edge case
- [ ] Every new repository has an integration test against real Postgres
- [ ] Every new endpoint has 200/201/204, 401, 403/404, 422 e2e tests
- [ ] All tests follow AAA; none named `test_X_works` / `test_misc`
- [ ] No real time, network, or unseeded randomness
- [ ] No `@pytest.mark.flaky`, no commented-out tests
- [ ] Coverage on touched modules has not regressed (even while the gate is relaxed)
- [ ] Negative tests written before assuming the happy path works
