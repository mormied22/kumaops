# Release verification

The supported test environment and results are recorded in
[VALIDATION.md](VALIDATION.md). Repeatable commands and test boundaries are in
[INTEGRATION.md](INTEGRATION.md).

The client is pinned to `uptime-kuma-api2` 2.9.0 and the integration target is
Kuma 2.5.9. Passing that matrix does not establish compatibility with every v2
release: Kuma's internal management API can change.

## Automated coverage

- Read-only plans, reference resolution, repeat-run no-ops and refusal on drift
  or ambiguous identities.
- Partial-write recovery, lost acknowledgement handling, input validation and
  secret redaction in offline tests.
- A disposable Kuma server with HTTP/TCP/ping health, groups, notification
  assignments and weekly maintenance scope.
- Real monitor transitions through the Discord provider to a local receiver,
  maintenance suppression and alert resumption after maintenance is paused.
- Real 2FA enrollment, missing/invalid/expired/replayed-code rejection, and CLI
  plan/apply/plan with a fresh unused code for each login.
- The upstream maintenance model and Croner scheduler under a virtual clock:
  weekly DST offsets, duration timers, nonexistent and repeated local times.
  Database writes and broadcasts are stubbed only in that scheduler process.

## Stable-release criteria

- Run the opt-in real Discord test with a dedicated channel webhook and confirm
  both API acceptance and visible DOWN/UP messages. User/role mentions, if used,
  need their own check.
- Obtain a passing hosted CI matrix and pinned Linux integration run.
- Review the source, release archive, license and exact compatibility claims.
  Keep real configuration, secrets and raw infrastructure logs private.

## Verification limits

The runtime maintenance check activates and pauses a window. Natural start/end
boundaries and DST are exercised separately in the upstream scheduler process;
the complete server is not moved through a simulated clock change.

Further compatibility work includes untrusted TLS-certificate rejection,
reverse-proxy/subpath deployments, other Kuma releases and real network failures
at each write boundary. Offline fault tests do not replace network-fault testing.
Release notes should state the verified matrix and any remaining limitations.

## Archive contents

`tools/package_release.py` includes source, tests, examples, documentation, CI and
license files. It excludes real configuration, environment files, source checkouts,
databases, caches, build metadata, Git metadata and logs. Test fixtures intentionally
use loopback addresses and generated credentials.

## Deferred reverse proxy

A public-status-only Nginx proxy is outside this release. Adding one requires
checks for status assets, API/WebSocket routes, administration/login denial,
encoded-path normalization, upstream routing and tunnel interactions.
