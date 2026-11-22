# Find your first contribution

A useful contribution solves a concrete user problem, documents verified behavior or
makes a failure easier to understand. Start with a focused change, not a large redesign.
See [CONTRIBUTING.md](../CONTRIBUTING.md) for setup and checks.

## Small, well-scoped opportunities

### Document a private-CA deployment

Explain how to connect to a disposable HTTPS Kuma instance with a local CA bundle.
Use reserved example names and no real credentials. Include exact versions, expected
success and an untrusted-certificate failure. Keep the result in a focused guide.

### Exercise starter-file races and filesystem failures

Extend the existing setup tests to simulate a destination appearing between preflight
and creation, and a write failure after one file is created. Confirm existing contents
are preserved, output contains no secrets and the documented partial-setup behavior holds.

### Improve troubleshooting examples

Add a minimal sanitized reproduction and explanation for a real setup problem. Check
that commands work with the supported schema and keep operational secrets out of examples.

## Integration help

The real Discord delivery check needs a dedicated test channel. Run the opt-in procedure
in [INTEGRATION.md](INTEGRATION.md) and report sanitized acceptance/results, never the webhook.
Another valuable contribution is repeating the suite on an additional stable Kuma version
and recording the exact compatibility evidence.

## Larger changes

[Ownership-aware reconciliation](../ROADMAP.md) is the next substantial milestone.
Start with a design discussion covering target/namespace binding, persisted IDs,
last-applied fingerprints, three-way diffs and recovery. Updates/deletion must not
turn into a broad overwrite switch.

Use [Discussions](https://github.com/mormied22/kumaops/discussions) to agree on scope,
then a focused issue or pull request. Contributors do not need access to private
infrastructure or production credentials.
