# ChatGPT Desktop Archive

Unofficial, evidence-based archive of historical **ChatGPT Desktop for macOS** DMG releases.

The current ChatGPT desktop app brings Chat, Work, and Codex together in one application. Use this repository when you need to roll back to a previous macOS build or reinstall an older DMG after an update breaks your workflow.

Each archived release is captured from the official OpenAI-linked download URL and published with SHA-256 hashes, macOS signature checks, notarization checks, mounted DMG inventory, release notes, and a machine-readable manifest.

## Quick Links

- [Download archived ChatGPT Desktop releases](https://github.com/KonstantinMeleshkin/codex-desktop-archive/releases)
- [Latest captured manifest](manifest/latest.json)
- [Verification guide](docs/verification.md)
- [Release policy](docs/release-policy.md)
- [Manifest format](docs/manifest.md)

## Why This Exists

ChatGPT Desktop updates are useful, but sometimes a fresh build can break an important workflow. If you did not save the previous installer, rolling back can be difficult because the official download URL points to the current build.

This archive gives macOS users a transparent way to find an older ChatGPT Desktop DMG and verify what was captured. Codex remains part of the app and is covered by the same archived installer.

Common search phrases this project is meant to answer:

- download older ChatGPT Desktop version
- downgrade ChatGPT Desktop on macOS
- roll back ChatGPT Desktop after update
- previous ChatGPT Desktop DMG
- historical ChatGPT Desktop releases
- verified ChatGPT Desktop macOS installer archive

## What Is Archived

| Platform | Status | Evidence level |
| --- | --- | --- |
| macOS | Full DMG from the official OpenAI-linked download URL | Strong |

This project does not archive Codex CLI. Codex CLI has its own open-source release channel.

Windows is intentionally not archived. The current official Windows path uses a Store bootstrapper, which can install whatever version Microsoft Store resolves at install time. That does not provide the same historical rollback guarantee as archiving a complete macOS DMG.

## Download An Older macOS Version

1. Open the [Releases page](https://github.com/KonstantinMeleshkin/codex-desktop-archive/releases).
2. Choose the ChatGPT Desktop version you want to restore.
3. Download the `ChatGPT-Desktop-*-macos.dmg` asset and `codex-desktop-manifest.json` from the same release.
4. Verify the SHA-256 hash against the manifest before installing.

```bash
shasum -a 256 ChatGPT-Desktop-*-macos.dmg
```

The output should match the `sha256` field for the macOS artifact in `codex-desktop-manifest.json`.

## Official Source URLs

The workflow captures the macOS download linked from the official Codex page:

- Codex page: <https://openai.com/codex/>
- macOS DMG: <https://persistent.oaistatic.com/codex-app-prod/ChatGPT.dmg>
- OpenAI release note: <https://help.openai.com/en/articles/6825453-chatgpt-release-notes#the-new-chatgpt-desktop-app-brings-chat-work-and-codex-together>

The current desktop app is the unified ChatGPT application: Chat, Work, and Codex are delivered together. New archive tags therefore use the `chatgpt-v<version>` series; older `desktop-v<version>` tags remain historical Codex Desktop releases.

## Verification Model

Every release is based on a manifest. The manifest records:

- source URL and effective URL observed by the downloader
- selected HTTP headers
- SHA-256 and byte size
- GitHub Actions run id
- workflow commit SHA
- app version/build when inspectable
- mounted DMG inventory
- macOS signature, Gatekeeper, and notarization results
- known limitations

For macOS, the workflow verifies the DMG and checks that the ChatGPT app is signed and notarized as:

```text
Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2)
```

It also checks the expected app identity, bundle metadata, and mounted image contents before publication.

## Manual Verification

After checking the SHA-256 hash, you can also verify the disk image and app signature locally:

```bash
hdiutil verify ChatGPT-Desktop-*-macos.dmg
hdiutil attach -readonly -nobrowse ChatGPT-Desktop-*-macos.dmg
codesign --verify --verbose=4 "/Volumes/ChatGPT Installer/ChatGPT.app"
spctl -a -vv -t exec "/Volumes/ChatGPT Installer/ChatGPT.app"
xcrun stapler validate "/Volumes/ChatGPT Installer/ChatGPT.app"
hdiutil detach "/Volumes/ChatGPT Installer"
```

See [docs/verification.md](docs/verification.md) for the full verification guide.

## Release Policy

The capture workflow runs once per day at `06:17 UTC` and can also be started manually with `workflow_dispatch`.

The workflow creates a new release only when the captured artifact identity changes. It skips release creation when the current capture has the same app version/build and artifact hashes as the latest manifest.

Existing release assets are not silently overwritten. The workflow does not use `gh release upload --clobber`.

Publication is separated from capture and read-only verification. The final publish job is the only job with `contents: write`, and it re-inspects the macOS DMG before publishing.

Skipped captures still verify the already-published GitHub Release against `manifest/latest.json`, including asset hashes, attached manifest, release notes, and tag target.

## Limits

This project can prove what its GitHub Actions workflow downloaded, verified, and published.

It cannot mathematically prove what OpenAI served on a historical date unless OpenAI or another independent source published the historical hash for that exact file.

This project is not affiliated with OpenAI.
