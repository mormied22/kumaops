# Contributing

Bug reports, compatibility results and focused improvements are welcome.

## Development setup

Use Python 3.11 or newer and a clean virtual environment. From the repository root:

```sh
python -m pip install -r requirements-dev.txt
python -m pip install --no-deps -e .
python -m pytest -q
python -m ruff check .
python -m ruff format --check src tests tools
```

The default test run is offline. Opt-in integration cases are skipped unless an
upstream checkout is supplied. Follow [INTEGRATION.md](docs/INTEGRATION.md) to run
the disposable Kuma server and scheduler checks. Use a dedicated test channel for
the optional real Discord test.

## Reporting a bug

Include the KumaOps, Python, operating-system, Kuma and client versions, the command
used, expected behavior and a minimal sanitized configuration. Replace infrastructure
names and endpoints with examples. Do not share passwords, authentication codes,
webhooks, environment files, database files or raw logs containing private data.

Describe uncertain writes carefully: an operation may succeed on the server before
its acknowledgement is lost. Inspect the server and re-plan before retrying.

## Pull requests

Keep changes focused and explain their effect on existing configurations. Include
tests for changed behavior, particularly idempotency, authentication, resource
matching or API normalization. Preserve secret redaction and fail-closed behavior.
State the exact upstream versions used for any compatibility claim.

Contributions are provided under the repository's MIT license. Third-party code
must retain its attribution and use a compatible license.
