# 0.2 release review

Reviewed against the public repository on 21 November 2026. This record describes
engineering findings and the implemented response, not a production certification.

| Finding | Response |
| --- | --- |
| CI, ignore rules and environment templates absent from the public upload | Restored tracked dotfiles and archive inclusion |
| Getting started required manual file assembly | Exclusive offline starter setup with a minimal monitor |
| Existing drift stopped at the first resource and lacked useful detail | Read-only collection of conflicts, with field names and no raw values |
| A normal plan returned success despite pending resources | Dedicated check mode with an actionable drift exit code |
| Automation had to parse prose or risk interactive input | Versioned JSON and explicit unattended operation |
| Monitor timing and HTTP behavior could not be configured | Validated supported fields, pinned-client and live regression coverage |
| Private CA deployments lacked a usable trust control | Explicit CA bundle forwarding without an insecure mode |
| Concurrent local applies could duplicate creates | Exclusive per-config-directory apply locks; distributed coordination remains out of scope |
| Malformed typed values could escape validation | Field type checks, malformed endpoint checks and alias rejection |
| No public project direction or vulnerability guidance | Roadmap, architecture, security policy and contribution templates |

## Deliberate remaining boundaries

Durable ownership, reviewed updates, imports and deletion need a three-way state
model with recovery semantics. The additive engine does not claim these features.
Real Discord-channel acceptance and hosted CI still require separate qualification.
The live matrix targets one pinned Kuma release; expanding it remains a milestone.
