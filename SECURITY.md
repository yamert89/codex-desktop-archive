# Security Policy

## Supported Scope

Security reports should focus on this repository's archival workflow, scripts, manifests, and release publication process.

Examples:

- workflow can publish unverified artifacts
- manifest can be forged or generated incorrectly
- release assets can be overwritten silently
- verification docs are dangerously wrong
- scripts trust unpinned or unexpected sources

## Not In Scope

- Vulnerabilities in ChatGPT or Codex themselves
- Vulnerabilities in OpenAI's download infrastructure
- Requests for official OpenAI support

## Reporting

Please open a GitHub issue if the report can be public.

If the report involves a sensitive exploit path, avoid posting exploit details publicly. Open a minimal issue saying that a private security report is needed, and the maintainer will coordinate a private channel.

## Security Principles

- No silent release overwrites.
- No custom repackaging of ChatGPT Desktop installers.
- No stronger claims than stored evidence supports.
- Linux DEB releases must pass package metadata and payload inventory checks before publication.
- Linux DEB packages must come from the approved OpenAI-linked amd64 and arm64 source URLs.
- Linux DEB maintainer scripts must be inventoried without being executed by the workflow.
