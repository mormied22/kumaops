# KumaOps

### YAML provisioning for Uptime Kuma

Define your monitors, Discord notifications and recurring maintenance in one
configuration file. Preview the changes, apply them, then run again without
creating duplicates.

**Release candidate: `v0.1.0-rc.1`** · Python 3.11+ · MIT licensed

> Verified against Uptime Kuma **2.5.9**. Actual Discord-channel delivery remains
> unverified; provider behavior is tested with a local receiver. See the
> [validation record](docs/VALIDATION.md) for the exact scope.

## What it does

| Feature | Included in this release |
| --- | --- |
| Monitors | HTTP, TCP port and ping checks |
| Organization | One level of monitor groups |
| Notifications | Discord integrations assigned to selected monitors |
| Maintenance | Weekly recurring windows with explicit IANA timezones |
| Preview | Read-only `--plan` and offline `--validate` |
| Apply | Create missing resources and add missing maintenance assignments |
| Authentication | Username/password and explicit 2FA support |
| Repeat runs | Reuse matching resources; stop on conflicting settings |

KumaOps is additive. It does not update or delete existing resource settings.
Use it first with a disposable Kuma instance and a dedicated namespace.

## Quick start

### 1. Install

Clone this repository or extract the source archive, then open its root directory.
Create and activate a virtual environment:

**Linux / macOS**

```sh
python -m venv .venv
. .venv/bin/activate
```

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the application:

```sh
python -m pip install -r requirements.txt
python -m pip install --no-deps .
```

Use a clean environment: other Kuma client packages can share the same Python
import name and should not be installed alongside this project's pinned client.

### 2. Configure

Copy `examples/minimal.yaml` to `config.yaml` and `.env.example` to `.env`.
Set `KUMA_URL` to your Kuma base URL. Provide credentials in your local environment
or enter them interactively when running the CLI. Keep real environment files private.

The minimal configuration creates one HTTP check:

```yaml
version: 1
namespace: getting-started
monitors:
  website:
    type: http
    url: https://example.com
    interval: 60
```

Replace `https://example.com` with the endpoint you want to monitor. The
[complete example](examples/config.yaml) also includes groups, Discord and
inactive weekly maintenance. [Configuration reference →](docs/CONFIGURATION.md)

### 3. Preview, apply, verify

```sh
# Check the file without connecting to Kuma.
kumaops --config config.yaml --validate

# Read the server and preview the proposed actions.
kumaops --config config.yaml --env-file .env --plan

# Create the missing resources, then verify the result.
kumaops --config config.yaml --env-file .env --apply
kumaops --config config.yaml --env-file .env --plan
```

The last plan should report **0 actions**. Apply prints its current plan and
immediately performs it; it does not ask for another confirmation. New live
monitors can send alerts as soon as they begin checking their endpoints.

**Using 2FA?** Add `--two-factor` to each connected command to enter a six-digit
code through hidden input. Wait for a fresh, unused code between commands: Kuma
rejects reuse of the same code, even before it expires. For automation, inject a
fresh `KUMA_TOTP_CODE` through your secret-management system.

## Know before you apply

- Keep a Kuma backup and reserve your namespace for this tool.
- Run one writer per instance/namespace, including manual UI changes.
- Matching names and configured fields are reused. Conflicting or ambiguous
  matches stop execution; resources outside the configuration are left alone.
- Removing a YAML entry does not remove its server resource. Changing a key or
  namespace creates a new identity and may duplicate an existing check.
- A failed acknowledgement may follow a successful write. Inspect the server,
  then re-plan before retrying. There is no automatic rollback or write retry.

[Resource matching, drift and recovery →](docs/SAFETY.md)

## Maintenance and timezones

Maintenance defaults to **inactive**. Verify the monitor scope and schedule before
activating a window. Times use the specified timezone, not the machine running the
CLI. Windows must start and end on the same day.

For UK maintenance, a window such as **03:00–03:30 Europe/London** avoids the
clock-change hour. Missing and repeated local times have specific scheduler
behavior; see [the DST results](docs/INTEGRATION.md#europelondon-dst-behavior-characterized-for-259).

## Documentation

- [Configuration reference](docs/CONFIGURATION.md)
- [Safety and recovery](docs/SAFETY.md)
- [Verified versions and results](docs/VALIDATION.md)
- [Running the integration tests](docs/INTEGRATION.md)
- [Release verification](docs/VERIFICATION.md)
- [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

## Development

```sh
python -m pip install -r requirements-dev.txt
python -m pip install --no-deps -e .
python -m pytest -q
python -m ruff check .
python -m ruff format --check src tests tools
```

Default tests are offline. GitHub Actions is configured for Python 3.11–3.13 on
Linux and Windows, plus a Linux integration job with pinned Kuma 2.5.9 and a local
alert receiver. The first hosted CI run is pending. No real credentials or webhook
are required by CI. Maintainers can use the [release guide](docs/PUBLISHING.md).

## Scope and license

This release does not include automatic updates/deletions, arbitrary monitor
types, nested groups, status-page management or a public-status reverse proxy.

KumaOps uses the community [uptime-kuma-api2 client](https://github.com/pbarone/uptime-kuma-api2).
The internal Kuma API can change; other Kuma versions require their own checks.
This project is unofficial and is not affiliated with Uptime Kuma.

[MIT License](LICENSE). Uptime Kuma and the Python client retain their own licenses.
