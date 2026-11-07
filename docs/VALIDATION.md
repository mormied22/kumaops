# Validation record

Validated on **7 November 2026** using Windows x64, Python **3.12.14**, Node.js
**22.17.0**, Uptime Kuma **2.5.9** and `uptime-kuma-api2` **2.9.0**.

The upstream checkout was pinned to commit
`df601c58d9205562f34cfe5ef35264b341019d19`. No upstream source was modified.

| Check | Result |
| --- | --- |
| Offline pytest suite | **39 passed**; opt-in integration cases skipped in the default run |
| Opt-in integration suite | **4 passed, 1 skipped**, 283.42 seconds |
| Live HTTP, TCP and ping health; groups and assignments | Passed against the disposable 2.5.9 server |
| Plan/apply/re-plan, repeat-run no-op, configured drift refusal | Passed |
| Real 2FA login, missing/invalid/expired/replayed-code rejection | Passed |
| CLI plan/apply/plan with unused 2FA codes | Passed |
| Real monitor DOWN/UP through the Discord provider to a local receiver | Passed |
| Maintenance activation, alert suppression and resumption | Passed |
| Upstream maintenance model with virtual-clock DST/duration cases | Four scenarios passed |
| Ruff lint and formatting | Passed |
| Package installation and console entry point | Passed |
| Offline example schema validation | Passed |
| Installed dependency consistency (`pip check`) | Passed |
| Source distribution and universal Python wheel build | Passed |
| Source archive content/privacy scan | Passed |
| Actual Discord API acceptance and visible test-channel messages | **Not run: dedicated webhook still required** |
| GitHub Actions matrix | Configured; not run on GitHub |

Tests run against an isolated server with a generated disposable account,
loopback endpoints, reserved example domains and a nonfunctional webhook placeholder.
The real Discord test is explicitly opt-in and was skipped. The source archive excludes local
environments, test caches, generated metadata, local configuration, logs and
non-project files. The source scan checks private addresses, personal paths,
email addresses, numeric Discord IDs and real-looking webhook tokens. Loopback
addresses in test fixtures are intentional. A scan is
an additional check, not a replacement for a maintainer's review before publishing.

See [INTEGRATION.md](INTEGRATION.md) for reproducible commands and the exact scope
of the runtime and virtual-clock checks. The important findings are that Kuma
rejects reused 2FA codes, and that missing/repeated UK local times have specific
scheduler behavior. A UK 03:00-03:30 schedule avoids the clock-change hour.

See [VERIFICATION.md](VERIFICATION.md) for the remaining release gate. The live
maintenance test activates/pauses a window; natural boundary timers and DST are
exercised in the separate upstream model process. These results do not claim
full-server time travel, real Discord delivery, a passing GitHub CI run or
compatibility with untested Kuma versions/platforms.

The release-candidate publication edition updates documentation, examples and
package metadata. CLI behavior is unchanged from the functional verification
above; its offline suite and release packaging are rechecked independently.
