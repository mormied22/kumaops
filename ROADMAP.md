# Roadmap

KumaOps aims to make self-hosted monitoring repeatable and reviewable. Project
milestones are driven by demonstrated use cases and test evidence, not dates.

## 0.2 — usable automation foundation

- Starter configuration, strict validation and non-interactive operation.
- Redacted JSON and CI drift exit codes.
- Detailed conflict reporting and explicit monitor timing/HTTP controls.
- Verified TLS with custom trust bundles, local apply exclusion and reproducible tests.
- Remaining integration qualification: real Discord acceptance/channel confirmation.
- Hosted CI passed for the merged 0.2.0 commit; see the validation record.

## 0.3 — ownership-aware reconciliation

- Persist resource IDs and last-applied field fingerprints, bound to target/namespace.
- Explicit import/adoption with a reviewable plan.
- Three-way diffs between last-applied, desired and current server settings.
- Opt-in updates which preserve unmanaged fields and block unexpected concurrent edits.
- Recovery tests at each acknowledgement boundary before enabling deletion.

## 0.4 — broader monitoring workflows

- Sanitized export of existing deployments and migration guidance.
- Additional monitor types prioritized through concrete user requirements.
- Environment overlays, reusable groups and notification providers.
- Compatibility fixtures for multiple stable Kuma versions.

## 1.0 — supported lifecycle

- Documented compatibility/deprecation policy and upgrade paths.
- Proven recovery, ownership, review and release-signing workflows.
- Maintainer capacity and repeatable release qualification.

The status-only reverse proxy is a separate future component requiring route,
normalization, WebSocket and upstream-security testing. It is not bundled here.
