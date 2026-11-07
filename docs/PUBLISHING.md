# Maintainer release guide

## Prepare a release

1. Run the offline checks in [CONTRIBUTING.md](../CONTRIBUTING.md) and the pinned
   integration suite in [INTEGRATION.md](INTEGRATION.md).
2. Update [VALIDATION.md](VALIDATION.md) with the exact versions and results.
   Keep real webhooks, authentication codes and raw logs out of the report.
3. Update `pyproject.toml`, `src/kumaops/__init__.py` and `CHANGELOG.md`. Use a
   prerelease version until the stable-release criteria in
   [VERIFICATION.md](VERIFICATION.md) are met.
4. Build and package the artifacts:

```sh
python -m build --no-isolation
python tools/package_release.py
```

The package script creates an allowlisted source ZIP and SHA-256 checksums in
`dist/`. Review the archive, examples and license attribution before publishing.

## Initial GitHub upload

Create an empty repository named `kumaops` under `mormied22`. Leave the README,
license and gitignore options unchecked because these files are already included.
From an extracted source directory:

```sh
git init -b main
git add .
git diff --cached --check
git status --short
git commit -m "Initial KumaOps release candidate"
git remote add origin https://github.com/mormied22/kumaops.git
git push -u origin main
```

These commands assume a new, empty repository. Inspect existing repositories and
remotes before changing them. Use your normal GitHub authentication and preferred
Git author identity; no credentials belong in the repository URL.

## Publish the release

Wait for the offline matrix and Kuma integration job in Actions to pass. Draft a
release from `main` using tag `v0.1.0-rc.1` and mark it **This is a pre-release**.
Attach the source ZIP, wheel, source distribution and `SHA256SUMS.txt` from `dist/`.
Do not attach environment files, databases or test logs.

State the tested Kuma version and remaining real Discord-delivery limitation in
the release notes. Publish a stable tag only after the stable-release checks pass.
