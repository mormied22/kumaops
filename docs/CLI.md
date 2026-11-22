# CLI and automation contract

Choose exactly one mode. Existing `--config`, `--env-file`, `--plan`, `--apply`,
`--validate`, `--two-factor` and `--allow-http` workflows remain supported.

| Mode | Server connection | Writes | Result |
| --- | --- | --- | --- |
| `--init` | No | Local starter config/environment files only | Refuses either existing destination |
| `--validate` | No | No | Checks YAML structure, references and option values |
| `--plan` | Yes | No | Missing resources, assignments and configured conflicts |
| `--check` | Yes | No | Drift gate for unattended jobs |
| `--apply` | Yes | Additive server writes | Refuses conflicts before writing; verifies every step |

`--config` defaults to `config.yaml`. `--init` creates `.env` beside that config
unless `--env-file` specifies another destination. Creation uses exclusive file
opens and restrictive POSIX permissions; Windows permissions follow directory ACLs.
A failure during setup can leave a created starter file; existing files are never
replaced. Secret values are not generated or written by setup.

## Output

`--format text` is the default. `--format json` emits one JSON document for results
or application errors and disables interactive credential entry. Argument-parser
errors and `--help`/`--version` retain standard command-line behavior.

The schema has `schema_version: 1`, `command`, `status`, `actions`, `message` and
`applied`. Status is one of `initialized`, `valid`, `in_sync`, `changes`, `conflict`,
`applied` or `error`. Each action has `operation`, `kind`, `key`; conflicts also have
`fields`. Actions never include desired/current values, URLs, credentials or
notification payloads. Treat resource keys as potentially operationally sensitive.

`applied` is the verified action count for successful apply, otherwise null.
An error does not imply zero writes: earlier operations may already have succeeded.
Plans describe the current read; they are not saved approval artifacts.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Successful operation; check is synchronized |
| `1` | Connection, filesystem or unexpected operational failure |
| `2` | Invalid input, rejected login, safety refusal or a conflicting plan/apply |
| `3` | Check found additions or conflicts; no server writes were made |

A plan containing additions returns `0`; use `--check` for a drift gate. Ambiguous
identities or malformed server snapshots are safety errors (`2`), not normal drift.
`--validate` does not check environment secrets or server compatibility.

## Connection controls

- `--non-interactive`: fail if credentials are absent; never request terminal input.
- `--two-factor`: hidden interactive authenticator entry; use a fresh unused code.
- `--timeout N`: management API timeout, 1–300 seconds; default 15.
- `--ca-bundle FILE`: custom trusted CA file, with TLS verification still enabled.
- `--allow-http`: explicit plaintext opt-in for trusted test networks/tunnels.
- `--version`: installed package version, without connecting.

Process environment overrides an explicit environment file, including empty values.
No environment file is searched automatically. Do not pass credentials as command
arguments or commit them to version control.

## Apply exclusion

A lock is created under `<config-directory>/.kumaops/locks/`, keyed by target URL
and namespace. A normal exit, including exceptions, releases it. After a crash,
confirm the owning process has stopped before deleting a stale lock. Different
configuration directories, URL aliases, hosts and other tools are outside this
local exclusion mechanism. Keep the single-writer operational requirement.
