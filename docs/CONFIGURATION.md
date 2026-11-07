# Configuration reference


See the [complete example](../examples/config.yaml). Unknown fields, duplicate YAML
keys, unsupported types and broken references fail validation.

| Section | Supported settings |
| --- | --- |
| Root | `version: 1`, `namespace` (lowercase letters, digits and hyphens) |
| `notifications` | Resource key, `webhook_env`, optional `prefix` |
| `groups` | Resource key with an empty mapping; one level of groups |
| `monitors` | `type: http/ping/port`, `url` or `hostname`, `port` for TCP; optional `group`, `interval`, `notifications` |
| `maintenance` | `timezone`, `weekdays`, `start_date`, `start`, `end`, `monitors`, optional `active` |

Resource keys use lowercase letters, digits and hyphens, starting with a letter.
Display identities are `KumaOps / <namespace> / <key>`. Monitor and group keys
share one namespace. Notification and maintenance keys are separate.

Monitors default to a 60-second interval (minimum 20). HTTP checks use the
client/server defaults for accepted status codes, request method, retry behavior
and TLS checking. v0.1 exposes no arbitrary API payloads, HTTP credentials, tags,
dependency trees or secret interpolation into monitor URLs. Avoid secrets in
URLs, names and message prefixes. Discord webhook URLs are read only from the
named environment variable; only the standard `https://discord.com/api/webhooks/…`
form is accepted. Notifications are not made default and are attached only to
configured monitors. KumaOps never sends an explicit test notification; newly
provisioned live monitors can still send real alerts.

Maintenance uses `recurring-weekday`: Sunday=0 through Saturday=6, quoted
`YYYY-MM-DD` start date and `HH:MM` local times. Windows must end later on the
same day; split overnight windows. Maintenance defaults to **inactive**.
Timezone and daylight-saving execution belong to Kuma, not the CLI. Use
`Europe/London` for UK local time and verify DST behavior on the actual server.
The pinned 2.5.9 scheduler's DST behavior, including missing and repeated local
times, is characterized in [INTEGRATION.md](INTEGRATION.md). Prefer 03:00–03:30
for UK maintenance to avoid a window crossing the clock-change hour.
There is no automatic matching of all monitors and no status-page assignment.


## Connection settings

| Variable | Purpose |
| --- | --- |
| `KUMA_URL` | Kuma base URL, normally HTTPS |
| `KUMA_USERNAME` | Account username; can also be entered interactively |
| `KUMA_PASSWORD` | Account password; hidden interactive input is available |
| `KUMA_TOTP_CODE` | Optional fresh, unused six-digit authenticator code |
| `DISCORD_WEBHOOK_URL` | Webhook referenced by the complete example |

Use `--env-file .env` to load an explicit file. Process environment values override
file values, including empty values. Parent directories are never searched and
values are not interpolated. Missing credentials fail in unattended sessions.

`--two-factor` reads an authenticator code through hidden terminal input. Each
command opens a separate login: use a new, unused code for each command. Kuma
rejects replayed codes even within their validity period. The CLI never stores
login tokens or TOTP seeds and does not enroll or disable 2FA. Kuma metrics API
keys cannot authenticate the Socket.IO management API.

TLS certificate verification is enabled. Plain HTTP requires `--allow-http`; use
it only on a trusted test network or through a secure tunnel. Custom CA bundles,
reverse-proxy subpaths and nonstandard authentication are outside the verified
configuration.

## Example files

- [minimal.yaml](../examples/minimal.yaml): one HTTP monitor, no webhook required.
- [config.yaml](../examples/config.yaml): groups, HTTP/ping checks, Discord and
  inactive weekly maintenance. Replace example endpoints and provide your own webhook.
