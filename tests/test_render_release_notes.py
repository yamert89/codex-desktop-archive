import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_release_notes import render_release_notes


class RenderReleaseNotesTests(unittest.TestCase):
    def test_renders_linux_deb_metadata_without_title_header(self):
        manifest = {
            "captured_at": "2026-08-15T12:34:56Z",
            "source_page": "https://learn.chatgpt.com/docs/linux/linux-app",
            "release": {
                "title": "ChatGPT Desktop Linux DEB 26.803.81509",
                "evidence_level": "strong",
            },
            "artifacts": [
                {
                    "platform": "linux",
                    "format": "deb",
                    "architecture": "amd64",
                    "classification": "full-installer",
                    "sha256": "abc123",
                    "size": 123,
                    "source": {"url": "https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_amd64.deb"},
                    "package": {
                        "name": "chatgpt",
                        "version": "26.803.81509",
                        "architecture": "amd64",
                        "maintainer": "OpenAI <support@openai.com>",
                    },
                    "deb": {
                        "payload": {"file_count": 42, "unexpected_executable_payloads": []},
                        "maintainer_scripts": [{"name": "postinst"}],
                    },
                    "verification": {"passed": True},
                }
            ],
            "limitations": ["This project is not affiliated with OpenAI."],
        }

        notes = render_release_notes(manifest)

        self.assertNotIn("# ChatGPT Desktop Linux DEB 26.803.81509", notes)
        self.assertIn("linux deb amd64", notes)
        self.assertIn("Package version: `26.803.81509`", notes)
        self.assertIn("Architecture: `amd64`", notes)
        self.assertIn("DEB payload files: `42`", notes)
        self.assertIn("Unexpected executable payloads: none", notes)
        self.assertIn("chatgpt-deb-manifest.json", notes)


if __name__ == "__main__":
    unittest.main()
