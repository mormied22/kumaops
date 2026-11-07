# Plans, resource matching and recovery


This release is deliberately additive:

- Creates missing resources in dependency order; matches by exact reserved name.
- Reuses existing matches only when the configured fields agree. Monitor/group
  and maintenance descriptions also carry a namespace marker. Notifications
  have no description marker; their reserved name and configured fields identify them.
- Refuses ambiguous names, drift, unreadable data, unsupported server major versions
  and unexpected maintenance links before making the first write.
- Adds missing configured maintenance links, preserving the existing subset.
- Never calls update, delete, notification-test or global-assignment APIs.
  Removing YAML entries leaves server resources untouched. Changing a key or
  namespace creates a new identity and can produce duplicate monitoring.
- Replans before apply and after each acknowledged write. A missing acknowledgement
  stops immediately; a write may already have succeeded. Inspect the UI, then
  re-plan. Matching resources and partially linked maintenance can be resumed.

Matching is not proof of ownership. Reserve your namespace exclusively for this
tool and review collisions. Changed URLs, webhooks, intervals or schedules produce
an error rather than automatic updates. For v0.1, reconcile changes manually in
Kuma and your config, or use a deliberate new key after reviewing duplicates.
No rollback or transaction is offered; earlier successful actions remain after
a later failure. Keep a Kuma backup before applying.

**Run only one writer for an instance/namespace**, including UI changes and other
tools. The API provides no atomic compare-and-create or uniqueness guarantee;
replanning cannot prevent every concurrent race. List events may be cached or
delayed; uncertain verification fails closed rather than retrying a write.
The displayed plan includes resource keys only, never payloads, URLs or secrets.

Exit codes: `0` success (including a plan with pending actions), `2` invalid
configuration, rejected login or safety refusal, `1` connection/unexpected failure.

