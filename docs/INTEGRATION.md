# Repeatable verification

These tests start their own Kuma process on loopback, select a private SQLite
database and generate a disposable account. They accept a source checkout, never
an existing Kuma URL or real account. The OS clock is never changed. The fixture
stops the server and local receiver at the end; temporary databases and logs are
local test artifacts and must not be published.

Requires Node.js **22.17.0** (including its test virtual-clock API), Python 3.11+
and the Python development dependencies. Tested locally with Python 3.12/Windows.
CI is also configured for the pinned upstream on Linux; record its results after
the first GitHub run rather than assuming parity.

## Obtain the pinned upstream

Run from the KumaOps repository root:

```sh
git clone --depth 1 --branch 2.5.9 https://github.com/louislam/uptime-kuma.git .verification/uptime-kuma
```

Inside `.verification/uptime-kuma`, run:

```sh
npm ci --omit=dev --no-audit --no-fund
npm run download-dist
```

Then return to the KumaOps root:

```sh
python -m pytest tests/integration -q --live-kuma-source .verification/uptime-kuma --basetemp .verification/pytest --tb=short
```

The alert cycle takes several minutes because it honors real monitor intervals
and the client's default retry. Avoid running within ten minutes of midnight in
Europe/London because v0.1 deliberately restricts maintenance to same-day windows.
The test will refuse that boundary. Use a fresh temporary-directory name if a
previous run's files are locked by Windows. Stop an interrupted test's exact
process before rerunning; never broadly terminate all Node or Kuma processes.

## What the tests exercise

- Actual Socket.IO management calls and persistence against Kuma **2.5.9**
  (`df601c58d9205562f34cfe5ef35264b341019d19`) and client **2.9.0**.
- HTTP, TCP and ping checks, groups, notification assignments, inactive weekly
  maintenance, correct scope, repeat-run no-ops and refusal on drift.
- Real DOWN/UP transitions, maintenance suppression and resumption. In the
  default mode, only the exact nonfunctional test webhook is routed to a local
  receiver; other URLs are not redirected. This does not verify Discord itself.
- Fresh-account 2FA enrollment, valid login and rejection of missing, invalid
  expired and replayed codes; CLI plan/apply with a fresh unused code per invocation.
  The suite waits for new authenticator codes, adding about a minute.
  Enrollment/disable calls
  exist only in the test harness, not the KumaOps CLI.
- The actual upstream maintenance model and Croner scheduler under a virtual
  clock. Database writes, cache invalidation and list broadcasts are stubbed in
  this separate scheduler process. Status transitions and duration timers use
  upstream code. These are scheduler tests, not a time-travel test of a whole
  running Kuma server or Discord across a simulated DST change.

## Europe/London DST behavior characterized for 2.5.9

| Schedule | Observed behavior |
| --- | --- |
| Sunday 03:00, March 22 to March 29, 2026 | UTC start moves from 03:00 to 02:00; local start stays 03:00 |
| Sunday 03:00, October 18 to October 25, 2026 | UTC start moves from 02:00 to 03:00; local start stays 03:00 |
| March 29, 2026 at nonexistent 01:30 | Executes at 02:30 local / 01:30 UTC |
| October 25, 2026 at ambiguous 01:30 | Uses the later 01:30 occurrence / 01:30 UTC |

Maintenance duration is elapsed time derived from the configured wall-clock
start/end difference. A window crossing a clock change can therefore end at a
different wall-clock time than expected. Prefer a window such as **03:00–03:30**
for UK maintenance. Other timezones and upstream versions need their own checks.

## Real Discord delivery (explicit opt-in)

Create a dedicated Discord test channel and its webhook. Copy
`.env.discord-test.example` to `.env.discord-test`, then set
`DISCORD_TEST_WEBHOOK_URL` in that local file. Do not paste it into chat or commit
it. Supplying the following flag authorizes actual messages to that channel:

```sh
python -m pytest tests/integration -q --live-kuma-source .verification/uptime-kuma --discord-env-file .env.discord-test --basetemp .verification/pytest-discord --tb=short
```

The harness forwards the actual upstream Discord provider's requests to Discord
and records successful API acknowledgements with payloads in its local receiver.
It checks DOWN, UP, no alert while under maintenance and an alert after maintenance
is paused, followed by recovery. Inspect those messages in the test channel too;
there are no user or role mentions in the supplied configuration. The webhook
owner can remove the test messages/channel afterward.

The real-webhook test is skipped when the file flag is omitted. Never put this
secret in ordinary pull-request CI. No secrets, webhooks, raw server logs or local
database files belong in a test report. Avoid `--showlocals` with real secrets.
