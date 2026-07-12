import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from should_release import decide_release


def manifest(tag, mac_sha, mac_version="26.707.51957"):
    return {
        "schema_version": "1.0",
        "release": {
            "tag": tag,
            "title": f"ChatGPT Desktop {mac_version}",
            "identity": {
                "product": "chatgpt-desktop",
                "version": mac_version,
                "build": "5175",
            },
        },
        "artifacts": [
            {
                "platform": "macos",
                "classification": "full-installer",
                "sha256": mac_sha,
                "size": 400814855,
                "app": {"version": mac_version, "build": "5175"},
            },
        ],
    }


class DecideReleaseTests(unittest.TestCase):
    def test_releases_when_no_latest_manifest_exists(self):
        candidate = manifest("chatgpt-v26.707.51957", "mac-sha", mac_version="26.707.51957")

        decision = decide_release(None, candidate)

        self.assertTrue(decision["should_release"])
        self.assertEqual(decision["tag"], "chatgpt-v26.707.51957")
        self.assertEqual(decision["reason"], "no previous manifest")

    def test_skips_when_all_platform_identities_match(self):
        latest = manifest("chatgpt-v26.707.51957", "mac-sha", mac_version="26.707.51957")
        candidate = manifest("chatgpt-v26.707.51957", "mac-sha", mac_version="26.707.51957")

        decision = decide_release(latest, candidate)

        self.assertFalse(decision["should_release"])
        self.assertEqual(decision["reason"], "all artifact identities unchanged")

    def test_releases_when_macos_hash_changes_even_if_version_matches(self):
        latest = manifest("chatgpt-v26.707.51957", "old-mac-sha", mac_version="26.707.51957")
        candidate = manifest("chatgpt-v26.707.51957", "new-mac-sha", mac_version="26.707.51957")

        decision = decide_release(latest, candidate)

        self.assertTrue(decision["should_release"])
        self.assertIn("macos sha256 changed", decision["reason"])


if __name__ == "__main__":
    unittest.main()
