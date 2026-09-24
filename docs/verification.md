# Verification Guide

This guide explains how to verify a release from this archive.

## Files To Download

From a GitHub Release, download:

- `ChatGPT-Desktop-<version>-linux-amd64.deb` or `ChatGPT-Desktop-<version>-linux-arm64.deb`
- `chatgpt-deb-manifest.json`

The manifest is the source of truth for the expected hash, size, source URL, workflow run, package metadata, and verification results.

## Linux DEB

### 1. Compare SHA-256

```bash
sha256sum ChatGPT-Desktop-*-linux-*.deb
```

Compare the output with:

```json
artifacts[].sha256
```

for the artifact where:

```json
"platform": "linux",
"format": "deb",
"architecture": "amd64"
```

Use `"arm64"` when verifying the ARM64 package.

### 2. Inspect Package Metadata

```bash
dpkg-deb -I ChatGPT-Desktop-*-linux-amd64.deb
```

Confirm the package metadata matches the manifest:

- `Package: chatgpt`
- `Version`
- `Architecture`
- `Maintainer`
- dependency fields

### 3. Inspect Package Contents

```bash
dpkg-deb -c ChatGPT-Desktop-*-linux-amd64.deb
```

The manifest records the payload inventory and rejects unexpected executable payloads outside ordinary Linux package locations.

### 4. Inspect Maintainer Scripts Without Running Them

```bash
tmpdir="$(mktemp -d)"
dpkg-deb -e ChatGPT-Desktop-*-linux-amd64.deb "$tmpdir/control"
find "$tmpdir/control" -maxdepth 1 -type f -print
```

Maintainer scripts such as `postinst` or `prerm` are not executed by the workflow. The workflow records their names, sizes, and SHA-256 hashes.

### 5. Install Only After Verification

```bash
sudo apt install ./ChatGPT-Desktop-*-linux-amd64.deb
```

Use the `arm64` asset on ARM64 systems.

## Evidence Levels

`strong` means:

- both amd64 and arm64 DEB packages were captured
- artifact hashes and sizes were recorded
- source URL metadata was recorded
- package metadata was readable
- package name and architecture matched policy
- both packages reported the same version
- payload inventory was recorded
- maintainer scripts were inventoried without executing them
- no unexpected executable payloads were detected

`partial` means:

- the artifact hash and source metadata were recorded
- at least one stronger package-level verification step was unavailable

The publication workflow rejects partial manifests.
