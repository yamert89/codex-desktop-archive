#!/usr/bin/env python3
"""Fail-closed release policy checks for ChatGPT Linux DEB archive publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEB_URLS = {
    "amd64": "https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_amd64.deb",
    "arm64": "https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_arm64.deb",
}
EXPECTED_ARCHITECTURES = set(DEB_URLS)
EXPECTED_PACKAGE = "chatgpt"
EXPECTED_PRODUCT = "chatgpt-desktop-linux-deb"
REQUIRED_VERIFICATION_CHECKS = [
    "dpkg_deb_control_read",
    "dpkg_deb_payload_list",
    "expected_package",
    "expected_architecture",
    "version_present",
    "maintainer_present",
    "control_scripts_inspected",
    "no_suspicious_maintainer_scripts",
    "no_unexpected_executable_payloads",
]


class SecurityPolicyError(ValueError):
    """Raised when a release candidate violates archive security policy."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SecurityPolicyError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifacts_by_architecture(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = manifest.get("artifacts", [])
    result = {}
    for artifact in artifacts:
        architecture = artifact.get("architecture")
        _require(architecture not in result, f"duplicate DEB artifact for architecture: {architecture}")
        result[architecture] = artifact
    _require(set(result) == EXPECTED_ARCHITECTURES, "manifest must contain exactly amd64 and arm64 Linux DEB artifacts")
    return result


def _validate_source(source: dict[str, Any], architecture: str) -> None:
    expected_url = DEB_URLS[architecture]
    _require(source.get("url") == expected_url, f"{architecture} source URL is not approved")
    effective_url = source.get("effective_url")
    _require(effective_url == expected_url, f"{architecture} effective URL is not approved")
    parsed = urlparse(effective_url or "")
    _require(parsed.scheme == "https", f"{architecture} effective URL must use https")
    _require(parsed.netloc == "persistent.oaistatic.com", f"{architecture} effective URL host is not approved")
    _require(parsed.path == f"/codex-app-prod/linux/deb/latest/chatgpt_{architecture}.deb", f"{architecture} effective URL path is not approved")
    _require(source.get("http_status") == 200, f"{architecture} source HTTP status must be 200")


def _validate_deb_payload(artifact: dict[str, Any], version: str, architecture: str, *, label: str) -> None:
    _require(artifact.get("platform") == "linux", f"{label} platform must be linux")
    _require(artifact.get("format") == "deb", f"{label} format must be deb")
    _require(artifact.get("classification") == "full-installer", f"{label} must be a full installer")
    _require(artifact.get("architecture") == architecture, f"{label} architecture does not match manifest key")

    package = artifact.get("package") or {}
    _require(package.get("name") == EXPECTED_PACKAGE, f"{label} package name does not match ChatGPT")
    _require(package.get("architecture") == architecture, f"{label} package architecture does not match")
    _require(package.get("version") == version, f"{label} package version does not match release identity")
    _require(bool(package.get("maintainer")), f"{label} package maintainer is missing")

    deb = artifact.get("deb") or {}
    payload = deb.get("payload") or {}
    _require(isinstance(payload.get("entries"), list), f"{label} payload inventory is missing")
    _require(payload.get("file_count") == len(payload.get("entries") or []), f"{label} payload file count is inconsistent")
    _require(payload.get("unexpected_executable_payloads") == [], f"{label} has unexpected executable payloads")
    _require(isinstance(deb.get("maintainer_scripts"), list), f"{label} maintainer script inventory is missing")

    verification = artifact.get("verification") or {}
    checks = verification.get("checks") or {}
    _require(verification.get("passed") is True, f"{label} verification did not pass")
    _require(verification.get("expected_package") == EXPECTED_PACKAGE, f"{label} expected package does not match policy")
    _require(verification.get("expected_architecture") == architecture, f"{label} expected architecture does not match policy")
    _require(
        all(checks.get(name) is True for name in REQUIRED_VERIFICATION_CHECKS),
        f"{label} verification checks did not all pass",
    )


def validate_manifest(manifest: dict[str, Any]) -> None:
    release = manifest.get("release") or {}
    identity = release.get("identity") or {}
    workflow = manifest.get("workflow") or {}
    tag = release.get("tag")
    version = identity.get("version")

    _require(manifest.get("schema_version") == "1.0", "unsupported manifest schema")
    _require(
        re.fullmatch(r"[a-f0-9]{40}", workflow.get("commit_sha") or "") is not None,
        "workflow commit SHA is invalid",
    )
    _require(release.get("evidence_level") == "strong", "Linux DEB releases must have strong evidence")
    _require(isinstance(version, str) and re.fullmatch(r"[A-Za-z0-9.+~_-]+", version), "unsafe package version")
    _require(identity.get("product") == EXPECTED_PRODUCT, "manifest product must be chatgpt-desktop-linux-deb")
    _require(identity.get("package") == EXPECTED_PACKAGE, "manifest package must be chatgpt")
    _require(identity.get("architectures") == ["amd64", "arm64"], "manifest architectures must be amd64 and arm64")
    _require(tag == f"chatgpt-deb-v{version}", "unsafe release tag")
    _require(re.fullmatch(r"chatgpt-deb-v[A-Za-z0-9.+~_-]+", tag or ""), "unsafe release tag")

    artifacts = _artifacts_by_architecture(manifest)
    versions = {artifact.get("package", {}).get("version") for artifact in artifacts.values()}
    _require(versions == {version}, "all DEB package versions must match release identity")

    for architecture, artifact in artifacts.items():
        expected_filename = f"ChatGPT-Desktop-{version}-linux-{architecture}.deb"
        _require(artifact.get("filename") == expected_filename, f"{architecture} release filename does not match version")
        _require(re.fullmatch(r"[a-f0-9]{64}", artifact.get("sha256") or ""), f"{architecture} SHA-256 is invalid")
        _require(isinstance(artifact.get("size"), int) and artifact["size"] > 0, f"{architecture} artifact size is invalid")
        _validate_source(artifact.get("source") or {}, architecture)
        _validate_deb_payload(artifact, version, architecture, label=architecture)


def verify_asset_directory(
    manifest: dict[str, Any],
    asset_dir: Path,
    *,
    require_manifest_asset: bool,
    release_notes_path: Path | None = None,
) -> None:
    validate_manifest(manifest)
    artifacts = _artifacts_by_architecture(manifest)
    expected_files = {artifact["filename"] for artifact in artifacts.values()}
    if require_manifest_asset:
        expected_files.update({"chatgpt-deb-manifest.json", "release-notes.md"})

    actual_files = {path.name for path in asset_dir.iterdir() if path.is_file()}
    extra_files = actual_files - expected_files
    missing_files = expected_files - actual_files
    _require(not extra_files, f"unexpected release asset(s): {', '.join(sorted(extra_files))}")
    _require(not missing_files, f"missing release asset(s): {', '.join(sorted(missing_files))}")

    for artifact in artifacts.values():
        artifact_path = asset_dir / artifact["filename"]
        _require(artifact_path.stat().st_size == artifact["size"], f"{artifact['architecture']} release asset size does not match manifest")
        _require(_sha256(artifact_path) == artifact["sha256"], f"{artifact['architecture']} release asset SHA-256 does not match manifest")

    if require_manifest_asset:
        attached_manifest = json.loads((asset_dir / "chatgpt-deb-manifest.json").read_text(encoding="utf-8"))
        _require(attached_manifest == manifest, "attached manifest does not match candidate manifest")
    if release_notes_path is not None:
        _require(
            (asset_dir / "release-notes.md").read_bytes() == release_notes_path.read_bytes(),
            "release notes asset does not match expected release notes",
        )


def verify_local_artifact(manifest: dict[str, Any], artifact_path: Path, inspection_path: Path) -> None:
    validate_manifest(manifest)
    inspection = json.loads(inspection_path.read_text(encoding="utf-8"))
    architecture = inspection.get("package", {}).get("architecture")
    artifacts = _artifacts_by_architecture(manifest)
    artifact = artifacts.get(architecture)
    _require(artifact is not None, "fresh DEB inspection architecture is not in manifest")
    version = manifest["release"]["identity"]["version"]

    _require(artifact_path.stat().st_size == artifact["size"], f"{architecture} local artifact size does not match manifest")
    _require(_sha256(artifact_path) == artifact["sha256"], f"{architecture} local artifact SHA-256 does not match manifest")

    _validate_deb_payload(inspection, version, architecture, label=f"fresh {architecture} DEB inspection")

    for key in ["classification", "format", "package", "deb", "verification"]:
        _require(inspection.get(key) == artifact.get(key), f"fresh {architecture} DEB inspection does not match manifest")


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ChatGPT Linux DEB release security invariants.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest_parser = subparsers.add_parser("validate-manifest")
    manifest_parser.add_argument("--manifest", type=Path, required=True)

    assets_parser = subparsers.add_parser("verify-assets")
    assets_parser.add_argument("--manifest", type=Path, required=True)
    assets_parser.add_argument("--asset-dir", type=Path, required=True)
    assets_parser.add_argument("--require-manifest-asset", action="store_true")
    assets_parser.add_argument("--release-notes", type=Path)

    local_parser = subparsers.add_parser("verify-local-artifact")
    local_parser.add_argument("--manifest", type=Path, required=True)
    local_parser.add_argument("--artifact", type=Path, required=True)
    local_parser.add_argument("--inspection", type=Path, required=True)

    args = parser.parse_args()
    manifest = _load_manifest(args.manifest)

    if args.command == "validate-manifest":
        validate_manifest(manifest)
    elif args.command == "verify-assets":
        verify_asset_directory(
            manifest,
            args.asset_dir,
            require_manifest_asset=args.require_manifest_asset,
            release_notes_path=args.release_notes,
        )
    elif args.command == "verify-local-artifact":
        verify_local_artifact(manifest, args.artifact, args.inspection)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
