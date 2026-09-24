# Manifest Format

Every release includes `chatgpt-deb-manifest.json`.

The manifest is designed to be readable by humans and strict enough for scripts.

## Top-Level Fields

```json
{
  "schema_version": "1.0",
  "captured_at": "2026-08-15T12:34:56Z",
  "source_page": "https://learn.chatgpt.com/docs/linux/linux-app",
  "repository": "KonstantinMeleshkin/chatgpt-deb-archive",
  "workflow": {
    "run_id": "123456789",
    "commit_sha": "0123456789abcdef0123456789abcdef01234567"
  },
  "release": {
    "tag": "chatgpt-deb-v26.803.81509",
    "title": "ChatGPT Desktop Linux DEB 26.803.81509",
    "identity": {
      "product": "chatgpt-desktop-linux-deb",
      "version": "26.803.81509",
      "package": "chatgpt",
      "architectures": ["amd64", "arm64"]
    },
    "evidence_level": "strong"
  },
  "artifacts": [],
  "limitations": []
}
```

## Artifact Fields

Each artifact records:

- platform: `linux`
- format: `deb`
- architecture: `amd64` or `arm64`
- classification: `full-installer`
- filename
- SHA-256
- byte size
- source metadata
- package metadata from the DEB control file
- DEB payload inventory
- maintainer script inventory
- verification result

## Classifications

`full-installer`:

- The artifact is a complete DEB package for one architecture.
- Current captures require both `amd64` and `arm64`.

## Release Identity

When both DEB packages expose the same package version, release tags use:

```text
chatgpt-deb-v<version>
```

Example:

```text
chatgpt-deb-v26.803.81509
```

When package version is not available or does not match across architectures, tags fall back to:

```text
chatgpt-deb-capture-YYYY-MM-DD
```

Fallback manifests use `partial` evidence level. The publication workflow rejects partial manifests, so normal public releases require matching package versions and strong evidence.
