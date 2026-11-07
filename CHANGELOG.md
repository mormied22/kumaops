# Changelog

## 0.1.0-rc.1 — 2026-11-07

First public release candidate.

### Features

- YAML configuration for HTTP, TCP and ping monitors, plus monitor groups.
- Discord notifications assigned to explicitly configured monitors.
- Weekly recurring maintenance with IANA timezone support.
- Read-only plans, additive apply, repeat-run no-ops and refusal on configured drift.
- Interactive authentication and explicit two-factor authentication support.
- Offline tests, opt-in Kuma 2.5.9 integration tests and GitHub Actions checks.
- Minimal and complete examples, installation instructions and configuration reference.

### Known limitations

- Existing resource settings cannot be updated or deleted through the CLI.
- Actual Discord-channel delivery verification is still pending.
- Live compatibility is verified against Kuma 2.5.9 only.
- Maintenance windows must start and end on the same day.
- Only one writer may manage an instance/namespace at a time.
- No status-page or reverse-proxy configuration is included.

See [the validation record](docs/VALIDATION.md) for the exact test scope.
