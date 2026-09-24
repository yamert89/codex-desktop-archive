#!/usr/bin/env python3
"""Build release manifests for the ChatGPT Linux DEB archive."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
SOURCE_PAGE = "https://learn.chatgpt.com/docs/linux/linux-app"
DEB_URLS = {
    "amd64": "https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_amd64.deb",
    "arm64": "https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_arm64.deb",
}

LIMITATIONS = [
    "This project is not affiliated with OpenAI.",
    "Artifacts are archived from official OpenAI-linked Linux DEB download URLs.",
    "Historical byte identity cannot be proven without an OpenAI-published historical hash.",
    "This archive supports the Linux ChatGPT desktop app preview for Debian and Ubuntu systems.",
]


def file_identity(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "size": size}


def release_identity(artifacts: list[dict[str, Any]], captured_at: str) -> dict[str, Any]:
    versions = {
        artifact.get("package", {}).get("version")
        for artifact in artifacts
        if artifact.get("package", {}).get("version")
    }
    if len(versions) == 1:
        version = versions.pop()
        return {
            "tag": f"chatgpt-deb-v{version}",
            "title": f"ChatGPT Desktop Linux DEB {version}",
            "identity": {
                "product": "chatgpt-desktop-linux-deb",
                "version": version,
                "package": "chatgpt",
                "architectures": sorted(artifact["architecture"] for artifact in artifacts),
            },
            "evidence_level": "strong",
        }

    capture_date = captured_at[:10]
    return {
        "tag": f"chatgpt-deb-capture-{capture_date}",
        "title": f"ChatGPT Desktop Linux DEB capture {capture_date}",
        "identity": {
            "product": "chatgpt-desktop-linux-deb",
            "version": None,
            "package": "chatgpt",
            "architectures": sorted(artifact["architecture"] for artifact in artifacts),
        },
        "evidence_level": "partial",
    }


def build_manifest(
    *,
    captured_at: str,
    repository: str,
    workflow_run_id: str,
    workflow_sha: str,
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    sorted_artifacts = sorted(artifacts, key=lambda item: item.get("architecture", ""))
    release = release_identity(sorted_artifacts, captured_at)
    version = release["identity"].get("version")
    if version:
        for artifact in sorted_artifacts:
            artifact["filename"] = f"ChatGPT-Desktop-{version}-linux-{artifact['architecture']}.deb"

    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": captured_at,
        "source_page": SOURCE_PAGE,
        "repository": repository,
        "workflow": {
            "run_id": workflow_run_id,
            "commit_sha": workflow_sha,
        },
        "release": release,
        "artifacts": sorted_artifacts,
        "limitations": LIMITATIONS,
    }


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _artifact_from_inputs(
    *,
    architecture: str,
    artifact_path: Path,
    source_path: Path,
    inspection_path: Path,
) -> dict[str, Any]:
    source = _load_json(source_path)
    inspection = _load_json(inspection_path)
    identity = file_identity(artifact_path)
    result = {
        "platform": "linux",
        "format": "deb",
        "architecture": architecture,
        "filename": artifact_path.name,
        "sha256": identity["sha256"],
        "size": identity["size"],
        "source": source,
    }
    result.update(inspection)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a ChatGPT Linux DEB release manifest.")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--workflow-sha", required=True)
    parser.add_argument("--captured-at", default=_utc_now())
    parser.add_argument("--deb-artifact", action="append", type=Path, default=[])
    parser.add_argument("--deb-source", action="append", type=Path, default=[])
    parser.add_argument("--deb-inspection", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not (len(args.deb_artifact) == len(args.deb_source) == len(args.deb_inspection)):
        raise SystemExit("--deb-artifact, --deb-source, and --deb-inspection must be provided in matching counts")

    artifacts = []
    for artifact_path, source_path, inspection_path in zip(args.deb_artifact, args.deb_source, args.deb_inspection):
        inspection = _load_json(inspection_path)
        architecture = inspection.get("package", {}).get("architecture")
        if not architecture:
            raise SystemExit(f"Could not determine architecture from {inspection_path}")
        artifacts.append(
            _artifact_from_inputs(
                architecture=architecture,
                artifact_path=artifact_path,
                source_path=source_path,
                inspection_path=inspection_path,
            )
        )

    manifest = build_manifest(
        captured_at=args.captured_at,
        repository=args.repository,
        workflow_run_id=args.workflow_run_id,
        workflow_sha=args.workflow_sha,
        artifacts=artifacts,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
