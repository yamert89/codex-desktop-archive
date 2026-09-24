import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from should_release import decide_release


def manifest(tag, amd64_sha, arm64_sha, version="26.803.81509", architectures=None):
    architectures = architectures or ["amd64", "arm64"]
    artifacts = []
    for arch, sha in [("amd64", amd64_sha), ("arm64", arm64_sha)]:
        if arch not in architectures:
            continue
        artifacts.append(
            {
                "platform": "linux",
                "format": "deb",
                "architecture": arch,
                "classification": "full-installer",
                "sha256": sha,
                "size": 400814855,
                "source": {
                    "effective_url": f"https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_{arch}.deb"
                },
                "package": {"version": version, "architecture": arch},
            }
        )
    return {
        "schema_version": "1.0",
        "release": {
            "tag": tag,
            "title": f"ChatGPT Desktop Linux DEB {version}",
            "identity": {
                "product": "chatgpt-desktop-linux-deb",
                "version": version,
                "package": "chatgpt",
                "architectures": architectures,
            },
        },
        "artifacts": artifacts,
    }


class DecideReleaseTests(unittest.TestCase):
    def test_releases_when_no_latest_manifest_exists(self):
        candidate = manifest("chatgpt-deb-v26.803.81509", "amd64-sha", "arm64-sha")

        decision = decide_release(None, candidate)

        self.assertTrue(decision["should_release"])
        self.assertEqual(decision["tag"], "chatgpt-deb-v26.803.81509")
        self.assertEqual(decision["reason"], "no previous manifest")

    def test_skips_when_all_artifact_identities_match(self):
        latest = manifest("chatgpt-deb-v26.803.81509", "amd64-sha", "arm64-sha")
        candidate = manifest("chatgpt-deb-v26.803.81509", "amd64-sha", "arm64-sha")

        decision = decide_release(latest, candidate)

        self.assertFalse(decision["should_release"])
        self.assertEqual(decision["reason"], "all artifact identities unchanged")

    def test_releases_when_deb_hash_changes_even_if_version_matches(self):
        latest = manifest("chatgpt-deb-v26.803.81509", "old-amd64-sha", "arm64-sha")
        candidate = manifest("chatgpt-deb-v26.803.81509", "new-amd64-sha", "arm64-sha")

        decision = decide_release(latest, candidate)

        self.assertTrue(decision["should_release"])
        self.assertIn("amd64 sha256 changed", decision["reason"])

    def test_releases_when_package_version_changes(self):
        latest = manifest("chatgpt-deb-v26.803.81509", "amd64-sha", "arm64-sha", version="26.803.81509")
        candidate = manifest("chatgpt-deb-v26.900.1", "amd64-sha", "arm64-sha", version="26.900.1")

        decision = decide_release(latest, candidate)

        self.assertTrue(decision["should_release"])
        self.assertIn("package version changed", decision["reason"])

    def test_releases_when_architecture_set_changes(self):
        latest = manifest("chatgpt-deb-v26.803.81509", "amd64-sha", "arm64-sha", architectures=["amd64"])
        candidate = manifest("chatgpt-deb-v26.803.81509", "amd64-sha", "arm64-sha", architectures=["amd64", "arm64"])

        decision = decide_release(latest, candidate)

        self.assertTrue(decision["should_release"])
        self.assertIn("architecture set changed", decision["reason"])


if __name__ == "__main__":
    unittest.main()
