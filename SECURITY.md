# Security policy

The supported release line is 0.2.x. Security fixes target its latest patch release;
older versions may require an upgrade. The documented verification matrix defines
the tested platform and integration scope.

## Reporting

Private vulnerability reporting is enabled. Use GitHub's
[private reporting form](https://github.com/mormied22/kumaops/security/advisories/new)
for exploitable security issues; do not disclose them in public issues. Do not attach
passwords, one-time codes, webhooks, environment files, databases or raw private logs.

For ordinary bugs, use a sanitized public issue with the affected version and a
minimal reproduction. Revoke or rotate credentials exposed publicly; deleting a
post or commit alone does not revoke them.

## Operational model

Use a trusted management connection, keep certificate checks enabled and restrict
credential access. KumaOps authenticates to the management interface and can create
live monitors and notification integrations. It has no automatic rollback.

JSON output excludes values and raw upstream exceptions. It is not a sanitized
backup/export format. Local locking is not distributed coordination. Read
[the safety model](docs/SAFETY.md) before applying against an important instance.
