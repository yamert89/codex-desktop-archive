#!/usr/bin/env python3
"""Render GitHub release notes from a ChatGPT Linux DEB manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _artifact_section(artifact: dict[str, Any]) -> str:
    package = artifact.get("package") or {}
    deb = artifact.get("deb") or {}
    payload = deb.get("payload") or {}
    verification = artifact.get("verification") or {}
    source = artifact.get("source") or {}
    lines = [
        f"### linux deb {artifact.get('architecture', 'unknown')}",
        "",
        f"- Classification: `{artifact.get('classification', 'unknown')}`",
        f"- SHA-256: `{artifact.get('sha256')}`",
        f"- Size: `{artifact.get('size')}` bytes",
    ]
    if source.get("url"):
        lines.append(f"- Source URL: {source['url']}")
    if package.get("name"):
        lines.append(f"- Package: `{package['name']}`")
    if package.get("version"):
        lines.append(f"- Package version: `{package['version']}`")
    if package.get("architecture"):
        lines.append(f"- Architecture: `{package['architecture']}`")
    if package.get("maintainer"):
        lines.append(f"- Maintainer: `{package['maintainer']}`")
    if verification:
        lines.append(f"- Verification passed: `{bool(verification.get('passed'))}`")
    if payload.get("file_count") is not None:
        lines.append(f"- DEB payload files: `{payload['file_count']}`")
    if "unexpected_executable_payloads" in payload:
        unexpected = payload.get("unexpected_executable_payloads") or []
        value = "none" if not unexpected else ", ".join(f"`{item}`" for item in unexpected)
        lines.append(f"- Unexpected executable payloads: {value}")
    scripts = deb.get("maintainer_scripts") or []
    if scripts:
        script_names = ", ".join(f"`{script['name']}`" for script in scripts)
        lines.append(f"- Maintainer scripts: {script_names}")
    else:
        lines.append("- Maintainer scripts: none")
    return "\n".join(lines)


def render_release_notes(manifest: dict[str, Any]) -> str:
    release = manifest.get("release", {})
    limitations = manifest.get("limitations", [])
    sections = [
        f"- Captured at: `{manifest.get('captured_at')}`",
        f"- Evidence level: `{release.get('evidence_level', 'unknown')}`",
        f"- Source page: {manifest.get('source_page')}",
        "",
        "## Artifacts",
        "",
        "\n\n".join(_artifact_section(artifact) for artifact in manifest.get("artifacts", [])),
        "",
        "## Limitations",
        "",
    ]
    sections.extend(f"- {item}" for item in limitations)
    sections.append("")
    sections.append("See `chatgpt-deb-manifest.json` attached to this release for full machine-readable evidence.")
    sections.append("")
    return "\n".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render release notes from a manifest.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    with args.manifest.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_release_notes(manifest), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
