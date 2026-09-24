import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from make_manifest import build_manifest, file_identity, release_identity


class ManifestTests(unittest.TestCase):
    def test_file_identity_records_sha256_and_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chatgpt_amd64.deb"
            path.write_bytes(b"chatgpt amd64 package")

            identity = file_identity(path)

        self.assertEqual(identity["sha256"], "cae04b232b1c698cc0ee70e9423bf46ebd28f2f0aab329d841431a9372e438b9")
        self.assertEqual(identity["size"], 21)

    def test_release_identity_prefers_common_deb_package_version(self):
        artifacts = [
            {"platform": "linux", "format": "deb", "architecture": "amd64", "package": {"version": "26.803.81509"}},
            {"platform": "linux", "format": "deb", "architecture": "arm64", "package": {"version": "26.803.81509"}},
        ]

        identity = release_identity(artifacts, "2026-08-15T00:00:00Z")

        self.assertEqual(identity["tag"], "chatgpt-deb-v26.803.81509")
        self.assertEqual(identity["title"], "ChatGPT Desktop Linux DEB 26.803.81509")
        self.assertEqual(identity["identity"]["version"], "26.803.81509")
        self.assertEqual(identity["identity"]["architectures"], ["amd64", "arm64"])

    def test_release_identity_falls_back_to_capture_date(self):
        artifacts = [
            {"platform": "linux", "format": "deb", "architecture": "amd64", "classification": "full-installer"},
            {"platform": "linux", "format": "deb", "architecture": "arm64", "classification": "full-installer"},
        ]

        identity = release_identity(artifacts, "2026-08-15T12:34:56Z")

        self.assertEqual(identity["tag"], "chatgpt-deb-capture-2026-08-15")
        self.assertEqual(identity["evidence_level"], "partial")

    def test_build_manifest_contains_linux_deb_artifacts_and_limitations(self):
        artifacts = [
            {
                "platform": "linux",
                "format": "deb",
                "architecture": "amd64",
                "classification": "full-installer",
                "sha256": "amd64-sha",
                "size": 123,
                "source": {"url": "https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_amd64.deb"},
                "package": {"version": "26.803.81509", "architecture": "amd64"},
                "verification": {"passed": True},
            },
            {
                "platform": "linux",
                "format": "deb",
                "architecture": "arm64",
                "classification": "full-installer",
                "sha256": "arm64-sha",
                "size": 456,
                "source": {"url": "https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_arm64.deb"},
                "package": {"version": "26.803.81509", "architecture": "arm64"},
                "verification": {"passed": True},
            },
        ]

        manifest = build_manifest(
            captured_at="2026-08-15T12:34:56Z",
            repository="KonstantinMeleshkin/chatgpt-deb-archive",
            workflow_run_id="123",
            workflow_sha="abcdef",
            artifacts=artifacts,
        )

        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["repository"], "KonstantinMeleshkin/chatgpt-deb-archive")
        self.assertEqual(manifest["release"]["tag"], "chatgpt-deb-v26.803.81509")
        self.assertEqual(manifest["artifacts"][0]["filename"], "ChatGPT-Desktop-26.803.81509-linux-amd64.deb")
        self.assertEqual(manifest["artifacts"][1]["filename"], "ChatGPT-Desktop-26.803.81509-linux-arm64.deb")
        self.assertEqual(manifest["artifacts"][0]["platform"], "linux")
        self.assertEqual(manifest["artifacts"][0]["format"], "deb")
        self.assertIn("This project is not affiliated with OpenAI.", manifest["limitations"])


if __name__ == "__main__":
    unittest.main()
