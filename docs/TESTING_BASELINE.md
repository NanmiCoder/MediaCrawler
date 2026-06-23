# Testing Baseline

This document records the T021-1 test inventory and CI layering policy. It
describes known failures; it does not treat them as fixed.

## Test inventory

The repository contains 165 collected tests:

| Layer | Paths | Baseline |
| --- | --- | --- |
| Core regression | `douyin_scraper/tests`, `api/tests.py` | 89 passed |
| Legacy regression | `tests`, `test` | 53 passed, 9 code failures, 14 external skips by default |
| External integration | Selected tests under `test` | 14 tests, opt-in |

Before external tests were isolated and Redis defaults were aligned, the full
observed baseline was:

```text
142 passed / 15 failed / 8 skipped
```

With the T021-1 default external-service policy, the same 165 tests are
collected, but Redis/proxy integrations are skipped unless their environment is
explicitly enabled:

```text
142 passed / 9 failed / 14 skipped
```

No failing test is deleted or converted to `xfail`.

## CI layers

### Core regression gate

The blocking `core-tests` job runs:

```bash
pytest douyin_scraper/tests/ api/tests.py -q
```

These 89 tests are the pull-request merge gate and do not require Redis,
MongoDB, a proxy provider, or a real browser.

### Legacy baseline

The non-blocking `legacy-baseline` job runs:

```bash
pytest tests/ test/ -q
```

It keeps legacy coverage visible while the tracked failures are repaired.
The job is explicitly named as a known-failure baseline and uses
`continue-on-error: true`.

### External integration

Tests marked `external` are skipped unless
`MEDIACRAWLER_RUN_EXTERNAL_TESTS=1` is set. The external group currently
contains:

- 3 Redis cache tests;
- 3 proxy-pool tests that require Redis and a real proxy provider;
- 8 MongoDB integration tests.

Example for PowerShell:

```powershell
$env:MEDIACRAWLER_RUN_EXTERNAL_TESTS = "1"
python -m pytest test -m external -q
```

The CDP tests in `tests/test_cdp_browser.py` mock browser calls. They require
the Playwright Python package from the normal project requirements, but do not
download or launch a browser and are therefore not external integration tests.

## Markers

- `core`: stable merge-gate regression.
- `legacy`: compatibility coverage outside the merge gate.
- `external`: explicitly enabled external-service coverage.
- `redis`, `mongo`, `proxy`, `playwright`: dependency-specific groups.
- `known_fail`: an unresolved failure tracked by T021.

`core` and `legacy` are assigned by repository path in the root
`conftest.py`. Dependency and known-failure markers are attached to the
specific affected tests.

## Redis configuration

Redis uses these canonical variables:

```text
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

The legacy `REDIS_DB_HOST`, `REDIS_DB_PORT`, `REDIS_DB_PWD`, and
`REDIS_DB_NUM` names remain supported as fallbacks. Canonical variables take
precedence when both forms are present.

The local and Docker Compose defaults use no Redis password. An empty password
is passed to the Redis client as `None`, so it does not send `AUTH`. Inside
Compose, the API uses the service name `redis`; the Redis service does not
publish port 6379 to the host. When `REDIS_PASSWORD` is non-empty, Compose
passes the same value to the API and conditionally starts Redis with
`requirepass`.

Production deployments that require authentication must inject
`REDIS_PASSWORD` through their secret/environment mechanism and configure the
Redis server with the same password. Setting only the client password or only
the server password is invalid. Redis port 6379 must not be exposed publicly.

Pure Redis integration tests can be run against an explicitly available
service:

```powershell
$env:MEDIACRAWLER_RUN_EXTERNAL_TESTS = "1"
python -m pytest test/test_redis_cache.py -q
Remove-Item Env:\MEDIACRAWLER_RUN_EXTERNAL_TESTS
```

Proxy-pool tests remain separately marked `proxy` because they also require a
real proxy provider and credentials.

## Known failures

The original 15-failure baseline was:

| Group | Count | Follow-up |
| --- | ---: | --- |
| Legacy `/api/crawler` contract returns 404 | 8 | T021-3 |
| Redis authentication mismatch | 6 | Resolved by T021-2 configuration alignment |
| Excel Store Factory implementation mismatch | 1 | Separate T021-x or P2 |

After T021-2, the three pure Redis cache tests are no longer marked
`known_fail`. The three proxy-pool tests remain tracked because their real
provider dependency is not part of the default CI environment.

The API suite also emits closed-stream logging errors during shutdown without
failing pytest. The combined full-suite run also reports pending
`ExpiringLocalCache` cleanup tasks. These lifecycle issues remain assigned to
T021-5.

The backend `free_gb` and frontend `available_gb` health-field mismatch has no
current failing test and remains assigned to T021-4.

## Local commands

```bash
make test-core
make test-baseline
make test-all
make test-known-failures
make test-external
```

`test-baseline` and `test-known-failures` return a non-zero status while their
tracked failures remain. This is intentional visibility, not a merge gate.

## Follow-up order

1. T021-3: reconcile the legacy crawler route contract.
2. T021-4: align health response fields.
3. T021-5: repair test shutdown and logging lifecycle.
