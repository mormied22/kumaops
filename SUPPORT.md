# Support

Use [Discussions](https://github.com/mormied22/kumaops/discussions) for setup questions,
workflow ideas and sanitized deployment feedback. Use the
[bug report form](https://github.com/mormied22/kumaops/issues/new?template=bug.yml)
for reproducible incorrect behavior. Support is community-based; response times are
not guaranteed. Vulnerabilities follow [SECURITY.md](SECURITY.md).

## Common problems

### Login fails with 2FA

Wait for a fresh unused authenticator code for each connected command. Kuma rejects
replayed codes even while they are still within their validity period. For automated
jobs, inject a fresh code through the environment; JSON mode does not request input.

### A check exits with code 3

This means additions or configured conflicts exist, not that the check crashed. Read
the reported resource keys and fields. `--plan` is read-only; `--apply` creates missing
resources but will not overwrite conflicting settings. [Exit codes](docs/CLI.md).

### A plan reports conflicts after editing YAML

Updates and deletion are outside the current additive release. Reconcile the desired
and current settings deliberately; changing a namespace or key creates another identity.
Do not repeatedly retry an uncertain write without inspecting the server first.

### An apply reports a local lock

Check whether an apply is still running for the same config directory, target and
namespace. After confirming a crashed process has stopped, remove its stale lock in
`.kumaops/locks/`. The lock does not coordinate other hosts or configuration directories.

### The server uses a private certificate authority

Use `--ca-bundle path/to/ca.pem`. Keep certificate verification enabled. Use
`--allow-http` only on a trusted test network or through a secure tunnel.

## Share enough information safely

Include the KumaOps, Kuma, client, Python and operating-system versions; the command
used; expected/actual behavior; and a minimal sanitized configuration. Replace private
hosts and addresses with examples. Do not post credentials, codes, webhooks, environment
files, databases or raw private logs. [Configuration reference](docs/CONFIGURATION.md).
