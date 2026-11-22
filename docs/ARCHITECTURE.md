# Architecture

## Boundaries

- `config.py` loads strict, size-bounded YAML and validates supported fields and references.
  Duplicate keys, aliases, unknown settings and invalid field types are rejected.
- `engine.py` resolves logical resource references, compares configured fields, plans
  additive actions, and verifies writes without retrying uncertain mutations.
- `client.py` adapts the pinned Socket.IO client and explicitly refreshes monitor and
  maintenance lists. Notification delivery/list semantics remain upstream concerns.
- `operations.py` creates starter files exclusively and manages local apply locks.
- `cli.py` handles authentication and exposes text and versioned, value-free JSON output.

## Planning and apply

The engine identifies resources by reserved names; monitor/group and maintenance
records also carry a namespace description marker. These are collision safeguards,
not durable proof of ownership. Identical existing records can be reused. Configured
field conflicts are collected for plan/check and block apply. No automatic resource
settings updates, deletion or global notification assignment is implemented.

The complete strict plan is checked before the first write. Apply rereads after
mutations and validates expected progress. A lost acknowledgement stops immediately;
prior successful writes remain. Runtime state is not a transactional snapshot, and
there is no distributed uniqueness guarantee or rollback.

## Extension rules

New monitor fields require schema validation, exact client-boundary tests, plan
normalization and integration evidence. New output must never serialize raw payloads.
New mutations require explicit ownership and recovery semantics. Keep the pinned
upstream adapter separate from configuration and presentation logic.

## Tests

Offline tests use deterministic fakes and the installed client's request builders.
Opt-in tests start an isolated real server with generated credentials and loopback
endpoints. The Discord provider uses a local receiver by default. Real Discord
requires explicit credentials and is excluded from public CI. Scheduler edge cases
use the pinned upstream model and a virtual clock in a separate process.
