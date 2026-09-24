import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPTURE_WORKFLOW = ROOT / ".github" / "workflows" / "capture.yml"
PUBLISH_SCRIPT = ROOT / "scripts" / "publish_release.sh"


class WorkflowPolicyTests(unittest.TestCase):
    def test_skip_path_verifies_existing_release_assets(self):
        workflow = CAPTURE_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("Verify existing release when capture is unchanged", workflow)
        self.assertIn("if: steps.decision.outputs.should_release != 'true'", workflow)
        self.assertIn("./scripts/verify_existing_release.sh manifest/latest.json out/latest-release-notes.md", workflow)

    def test_workflow_runs_on_ubuntu(self):
        workflow = CAPTURE_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("runs-on: ubuntu-latest", workflow)
        self.assertNotIn("runs-on: macos-latest", workflow)

    def test_publish_job_reinspects_deb_artifacts(self):
        workflow = CAPTURE_WORKFLOW.read_text(encoding="utf-8")

        publish_section = workflow.split("  publish:", 1)[1]
        self.assertIn("python3 scripts/inspect_deb.py \"$amd64_asset\" out/final-publish-deb-amd64-inspection.json --architecture amd64", publish_section)
        self.assertIn("python3 scripts/inspect_deb.py \"$arm64_asset\" out/final-publish-deb-arm64-inspection.json --architecture arm64", publish_section)
        self.assertIn("python3 scripts/release_guard.py verify-local-artifact", publish_section)

    def test_workflow_uses_linux_deb_source_and_artifact_names(self):
        workflow = CAPTURE_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("DEB_AMD64_URL: https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_amd64.deb", workflow)
        self.assertIn("DEB_ARM64_URL: https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_arm64.deb", workflow)
        self.assertIn("artifacts/chatgpt_amd64.deb", workflow)
        self.assertIn("artifacts/chatgpt_arm64.deb", workflow)
        self.assertIn("ChatGPT-Desktop-${version}-linux-amd64.deb", workflow)
        self.assertIn("ChatGPT-Desktop-${version}-linux-arm64.deb", workflow)
        self.assertNotIn("ChatGPT-Desktop-${version}-macos.dmg", workflow)

    def test_publish_script_creates_git_tag_before_draft_release(self):
        script = PUBLISH_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("ensure_release_tag \"$tag\" \"$target_sha\"", script)
        self.assertLess(
            script.index("ensure_release_tag \"$tag\" \"$target_sha\""),
            script.index("gh release create \"$tag\""),
        )
        self.assertNotIn("--target \"$target_sha\"", script)


if __name__ == "__main__":
    unittest.main()
