# Changelog

## Unreleased

- Project header, live CI/release badges and a captured offline first-run preview.
- Documentation hub, support guide, community guidelines and contribution opportunities.
- Community routing for questions and private security reports.
- Include visual/community assets in source distributions and release archives.

## 0.2.0 — 2026-11-21

- Offline starter-project generation without overwriting files.
- Read-only CI drift checks with exit code 3 and field-level conflict reporting.
- Versioned redacted JSON output and explicit non-interactive mode.
- API timeout and custom CA bundle controls; TLS checks remain enabled.
- Monitor retries, retry intervals, HTTP timeouts, GET/HEAD, accepted status codes
  and certificate-expiry notifications.
- Local apply exclusion per configuration directory, target and namespace.
- Strict malformed-field/endpoint validation and YAML alias rejection.
- Restored environment templates, ignore rules and CI workflows missing from the public upload.
- Community contribution templates, security policy, roadmap and release artifact workflow.

Existing resource updates/deletion remain blocked. Real Discord-channel verification
and hosted CI results remain pending; see the validation record.

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
