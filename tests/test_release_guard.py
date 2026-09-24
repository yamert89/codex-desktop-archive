import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from release_guard import (
    SecurityPolicyError,
    validate_manifest,
    verify_asset_directory,
    verify_local_artifact,
)


AMD64_SHA = "cae04b232b1c698cc0ee70e9423bf46ebd28f2f0aab329d841431a9372e438b9"
ARM64_SHA = "b4c403d65eb420c307177788a98ca346f1b63ef5ffe3739199d7b3792cc7a012"
VERSION = "26.803.81509"


def artifact(arch, sha):
    return {
        "platform": "linux",
        "format": "deb",
        "architecture": arch,
        "classification": "full-installer",
        "filename": f"ChatGPT-Desktop-{VERSION}-linux-{arch}.deb",
        "sha256": sha,
        "size": 21,
        "source": {
            "platform": "linux",
            "format": "deb",
            "architecture": arch,
            "url": f"https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_{arch}.deb",
            "effective_url": f"https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_{arch}.deb",
            "http_status": 200,
            "headers": {"content-type": "application/vnd.debian.binary-package"},
        },
        "package": {
            "name": "chatgpt",
            "version": VERSION,
            "architecture": arch,
            "maintainer": "OpenAI <support@openai.com>",
            "installed_size": "123",
            "depends": "libgtk-3-0",
            "control_fields": {
                "package": "chatgpt",
                "version": VERSION,
                "architecture": arch,
                "maintainer": "OpenAI <support@openai.com>",
            },
        },
        "deb": {
            "payload": {
                "file_count": 2,
                "entries": [
                    {"mode": "drwxr-xr-x", "owner_group": "root/root", "size": 0, "date": "2026-08-01", "time": "00:00", "path": "./usr/"},
                    {"mode": "-rwxr-xr-x", "owner_group": "root/root", "size": 12, "date": "2026-08-01", "time": "00:00", "path": "./usr/bin/chatgpt"},
                ],
                "executable_payloads": ["./usr/bin/chatgpt"],
                "unexpected_executable_payloads": [],
            },
            "maintainer_scripts": [
                {"name": "postinst", "size": 10, "sha256": "a" * 64, "executable": True, "suspicious_patterns": []}
            ],
        },
        "verification": {
            "passed": True,
            "expected_package": "chatgpt",
            "expected_architecture": arch,
            "checks": {
                "dpkg_deb_control_read": True,
                "dpkg_deb_payload_list": True,
                "expected_package": True,
                "expected_architecture": True,
                "version_present": True,
                "maintainer_present": True,
                "control_scripts_inspected": True,
                "no_suspicious_maintainer_scripts": True,
                "no_unexpected_executable_payloads": True,
            },
        },
    }


def valid_manifest():
    return {
        "schema_version": "1.0",
        "captured_at": "2026-08-15T12:34:56Z",
        "source_page": "https://learn.chatgpt.com/docs/linux/linux-app",
        "repository": "KonstantinMeleshkin/chatgpt-deb-archive",
        "workflow": {"run_id": "123", "commit_sha": "a" * 40},
        "release": {
            "tag": f"chatgpt-deb-v{VERSION}",
            "title": f"ChatGPT Desktop Linux DEB {VERSION}",
            "identity": {
                "product": "chatgpt-desktop-linux-deb",
                "version": VERSION,
                "package": "chatgpt",
                "architectures": ["amd64", "arm64"],
            },
            "evidence_level": "strong",
        },
        "artifacts": [artifact("amd64", AMD64_SHA), artifact("arm64", ARM64_SHA)],
        "limitations": [],
    }


def valid_inspection(arch):
    return artifact(arch, AMD64_SHA if arch == "amd64" else ARM64_SHA) | {
        "filename": None,
        "sha256": None,
        "size": None,
        "source": None,
    }


class ReleaseGuardTests(unittest.TestCase):
    def test_valid_manifest_passes(self):
        validate_manifest(valid_manifest())

    def test_rejects_missing_architecture(self):
        manifest = valid_manifest()
        manifest["artifacts"] = [manifest["artifacts"][0]]

        with self.assertRaisesRegex(SecurityPolicyError, "exactly amd64 and arm64"):
            validate_manifest(manifest)

    def test_rejects_extra_architecture(self):
        manifest = valid_manifest()
        extra = artifact("riscv64", AMD64_SHA)
        extra["filename"] = f"ChatGPT-Desktop-{VERSION}-linux-riscv64.deb"
        manifest["artifacts"].append(extra)

        with self.assertRaisesRegex(SecurityPolicyError, "exactly amd64 and arm64"):
            validate_manifest(manifest)

    def test_rejects_wrong_package_name(self):
        manifest = valid_manifest()
        manifest["artifacts"][0]["package"]["name"] = "other"

        with self.assertRaisesRegex(SecurityPolicyError, "package name"):
            validate_manifest(manifest)

    def test_rejects_mismatched_package_versions(self):
        manifest = valid_manifest()
        manifest["artifacts"][1]["package"]["version"] = "26.900.1"

        with self.assertRaisesRegex(SecurityPolicyError, "all DEB package versions"):
            validate_manifest(manifest)

    def test_rejects_unexpected_source_url(self):
        manifest = valid_manifest()
        manifest["artifacts"][0]["source"]["effective_url"] = "https://example.com/chatgpt_amd64.deb"

        with self.assertRaisesRegex(SecurityPolicyError, "effective URL"):
            validate_manifest(manifest)

    def test_rejects_bad_sha(self):
        manifest = valid_manifest()
        manifest["artifacts"][0]["sha256"] = "bad"

        with self.assertRaisesRegex(SecurityPolicyError, "SHA-256"):
            validate_manifest(manifest)

    def test_rejects_unexpected_executable_payloads(self):
        manifest = valid_manifest()
        payload = manifest["artifacts"][0]["deb"]["payload"]
        payload["unexpected_executable_payloads"] = ["./tmp/run.sh"]
        manifest["artifacts"][0]["verification"]["checks"]["no_unexpected_executable_payloads"] = False

        with self.assertRaisesRegex(SecurityPolicyError, "unexpected executable payload"):
            validate_manifest(manifest)

    def test_verify_asset_directory_checks_hashes(self):
        manifest = valid_manifest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / f"ChatGPT-Desktop-{VERSION}-linux-amd64.deb").write_bytes(b"chatgpt amd64 package")
            (root / f"ChatGPT-Desktop-{VERSION}-linux-arm64.deb").write_bytes(b"chatgpt arm64 package")
            verify_asset_directory(manifest, root, require_manifest_asset=False)

    def test_verify_asset_directory_rejects_unexpected_assets(self):
        manifest = valid_manifest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / f"ChatGPT-Desktop-{VERSION}-linux-amd64.deb").write_bytes(b"chatgpt amd64 package")
            (root / f"ChatGPT-Desktop-{VERSION}-linux-arm64.deb").write_bytes(b"chatgpt arm64 package")
            (root / "unexpected.deb").write_text("bad", encoding="utf-8")

            with self.assertRaisesRegex(SecurityPolicyError, "unexpected release asset"):
                verify_asset_directory(manifest, root, require_manifest_asset=False)

    def test_verify_asset_directory_rejects_swapped_release_notes(self):
        manifest = valid_manifest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset_dir = root / "assets"
            asset_dir.mkdir()
            expected_notes = root / "expected-release-notes.md"
            expected_notes.write_text("trusted notes\n", encoding="utf-8")
            (asset_dir / f"ChatGPT-Desktop-{VERSION}-linux-amd64.deb").write_bytes(b"chatgpt amd64 package")
            (asset_dir / f"ChatGPT-Desktop-{VERSION}-linux-arm64.deb").write_bytes(b"chatgpt arm64 package")
            (asset_dir / "chatgpt-deb-manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            (asset_dir / "release-notes.md").write_text("changed notes\n", encoding="utf-8")

            with self.assertRaisesRegex(SecurityPolicyError, "release notes asset"):
                verify_asset_directory(
                    manifest,
                    asset_dir,
                    require_manifest_asset=True,
                    release_notes_path=expected_notes,
                )

    def test_verify_local_artifact_accepts_matching_fresh_inspection(self):
        manifest = valid_manifest()
        inspection = valid_inspection("amd64")
        for key in ["filename", "sha256", "size", "source"]:
            inspection.pop(key, None)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_path = root / f"ChatGPT-Desktop-{VERSION}-linux-amd64.deb"
            inspection_path = root / "inspection.json"
            artifact_path.write_bytes(b"chatgpt amd64 package")
            inspection_path.write_text(json.dumps(inspection), encoding="utf-8")

            verify_local_artifact(manifest, artifact_path, inspection_path)

    def test_verify_local_artifact_rejects_publish_side_inspection_mismatch(self):
        manifest = valid_manifest()
        inspection = valid_inspection("amd64")
        for key in ["filename", "sha256", "size", "source"]:
            inspection.pop(key, None)
        inspection["package"]["name"] = "other"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_path = root / f"ChatGPT-Desktop-{VERSION}-linux-amd64.deb"
            inspection_path = root / "inspection.json"
            artifact_path.write_bytes(b"chatgpt amd64 package")
            inspection_path.write_text(json.dumps(inspection), encoding="utf-8")

            with self.assertRaisesRegex(SecurityPolicyError, "fresh amd64 DEB inspection"):
                verify_local_artifact(manifest, artifact_path, inspection_path)


if __name__ == "__main__":
    unittest.main()
