# ChatGPT DEB Archive

Unofficial, evidence-based archive of historical **ChatGPT Desktop for Linux** DEB releases.

The Linux desktop app is available in preview for supported Debian and Ubuntu systems. Use this repository when you need to roll back to a previous DEB package or reinstall an older package after an update breaks your workflow.

Each archived release is captured from official OpenAI-linked Linux DEB download URLs and published with SHA-256 hashes, package metadata, payload inventory, release notes, and a machine-readable manifest.

## Quick Links

- [Download archived ChatGPT Linux DEB releases](https://github.com/KonstantinMeleshkin/chatgpt-deb-archive/releases)
- [Verification guide](docs/verification.md)
- [Release policy](docs/release-policy.md)
- [Manifest format](docs/manifest.md)

## Why This Exists

The official DEB download URLs point to the current package. If you did not save a previous installer, rolling back can be difficult.

This archive gives Debian and Ubuntu users a transparent way to find older ChatGPT Desktop DEB packages and verify what was captured.

Common search phrases this project is meant to answer:

- download older ChatGPT Desktop DEB
- downgrade ChatGPT Desktop on Ubuntu
- downgrade ChatGPT Desktop on Debian
- roll back ChatGPT Desktop Linux package
- historical ChatGPT Desktop Linux releases
- verified ChatGPT Linux DEB archive

## What Is Archived

| Platform | Architecture | Status | Evidence level |
| --- | --- | --- | --- |
| Linux DEB | amd64 | Full package from official OpenAI-linked download URL | Strong |
| Linux DEB | arm64 | Full package from official OpenAI-linked download URL | Strong |

This project only archives DEB packages. It does not archive RPM, Arch packages, AppImage builds, macOS DMGs, Windows installers, or Codex CLI.

## Download An Older Linux Version

1. Open the [Releases page](https://github.com/KonstantinMeleshkin/chatgpt-deb-archive/releases).
2. Choose the ChatGPT Desktop Linux DEB version you want to restore.
3. Download the DEB asset for your architecture and `chatgpt-deb-manifest.json` from the same release.
4. Verify the SHA-256 hash against the manifest before installing.

```bash
sha256sum ChatGPT-Desktop-*-linux-*.deb
```

The output should match the `sha256` field for the matching architecture in `chatgpt-deb-manifest.json`.

To inspect package metadata locally:

```bash
dpkg-deb -I ChatGPT-Desktop-*-linux-amd64.deb
dpkg-deb -c ChatGPT-Desktop-*-linux-amd64.deb
```

Install with `apt` only after checking the package you downloaded:

```bash
sudo apt install ./ChatGPT-Desktop-*-linux-amd64.deb
```

Use the `arm64` asset on ARM64 systems.

## Official Source URLs

The workflow captures the Linux DEB downloads linked from the official ChatGPT Linux app documentation:

- Linux app documentation: <https://learn.chatgpt.com/docs/linux/linux-app>
- amd64 DEB: <https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_amd64.deb>
- arm64 DEB: <https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_arm64.deb>

## Verification Model

Every release is based on a manifest. The manifest records:

- source URL and effective URL observed by the downloader
- selected HTTP headers
- SHA-256 and byte size
- GitHub Actions run id
- workflow commit SHA
- package name, version, architecture, maintainer, and dependencies
- DEB payload inventory
- maintainer script inventory and hashes
- known limitations

The workflow does not install the package. It inspects DEB metadata and package contents without executing maintainer scripts.

## Release Policy

The capture workflow runs once per day at `06:17 UTC` and can also be started manually with `workflow_dispatch`.

The workflow creates a new release only when the captured artifact identity changes. It skips release creation when the current capture has the same package version, architecture set, source identity, and artifact hashes as the latest manifest.

Existing release assets are not silently overwritten. The workflow does not use `gh release upload --clobber`.

Publication is separated from capture and read-only verification. The final publish job is the only job with `contents: write`, and it re-inspects both DEB packages before publishing.

Skipped captures still verify the already-published GitHub Release against `manifest/latest.json`, including asset hashes, attached manifest, release notes, and tag target.

## Limits

This project can prove what its GitHub Actions workflow downloaded, inspected, and published.

It cannot mathematically prove what OpenAI served on a historical date unless OpenAI or another independent source published the historical hash for that exact file.

This project is not affiliated with OpenAI.
