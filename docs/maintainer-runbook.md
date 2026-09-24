# Maintainer Runbook

## Routine Operation

The scheduled workflow runs daily at `06:17 UTC`. It can also be run manually with `workflow_dispatch`.

Expected outcomes:

- New ChatGPT Desktop Linux DEB version or artifact bytes: workflow publishes a new release.
- Same package version and artifact bytes: workflow skips release creation after verifying the existing GitHub Release still matches `manifest/latest.json`.
- Verification failure: workflow fails and publishes nothing.

The first successful Linux DEB run creates the first `chatgpt-deb-v<version>` release and writes `manifest/latest.json`.

## Manual Run

Use GitHub Actions:

1. Open the `Capture ChatGPT Linux DEB` workflow.
2. Run `workflow_dispatch`.
3. Inspect the workflow summary.
4. If a release was created, verify the attached manifest and release notes.

## Before Publicizing The Repository

Check:

- README is current.
- `SECURITY.md` is present.
- The latest release has `chatgpt-deb-manifest.json`.
- The latest release has both amd64 and arm64 DEB assets.
- The latest release notes include hashes and limitations.
- The workflow has not used `--clobber`.

## Failure Handling

If DEB package verification fails:

- do not publish the artifact
- check whether the official source URL changed
- check whether package metadata changed intentionally
- open an issue with the captured failure details

If a tag already exists with different bytes:

- do not overwrite it
- open an issue
- compare the existing release manifest with the candidate manifest
- publish a corrected release only with explicit maintainer review

## Local Test Commands

```bash
python3 -m unittest discover -s tests -v
bash -n scripts/capture_source.sh
bash -n scripts/publish_release.sh
bash -n scripts/verify_existing_release.sh
python3 -m py_compile scripts/inspect_deb.py scripts/make_manifest.py scripts/render_release_notes.py scripts/should_release.py scripts/release_guard.py
```
