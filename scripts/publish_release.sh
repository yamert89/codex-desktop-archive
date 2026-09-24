#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 6 ]; then
  echo "usage: $0 <manifest-json> <release-notes-md> <amd64-artifact> <arm64-artifact> <amd64-inspection-json> <arm64-inspection-json>" >&2
  exit 64
fi

manifest_path="$1"
release_notes_path="$2"
amd64_artifact_path="$3"
arm64_artifact_path="$4"
amd64_inspection_path="$5"
arm64_inspection_path="$6"

tmpdir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmpdir"
}
trap cleanup EXIT

read_manifest_field() {
  python3 - "$manifest_path" "$1" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
value = manifest
for part in sys.argv[2].split("."):
    if isinstance(value, list):
        value = value[int(part)]
    else:
        value = value[part]
print(value)
PY
}

artifact_filename_for_arch() {
  python3 - "$manifest_path" "$1" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
arch = sys.argv[2]
for artifact in manifest["artifacts"]:
    if artifact["architecture"] == arch:
        print(artifact["filename"])
        raise SystemExit(0)
raise SystemExit(f"missing artifact for {arch}")
PY
}

commit_manifest() {
  local tag="$1"
  local history_path="manifest/history/${tag}.json"

  mkdir -p manifest/history
  cp "$manifest_path" "$history_path"
  cp "$manifest_path" manifest/latest.json

  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  git add manifest/latest.json "$history_path"

  if ! git diff --cached --quiet; then
    git commit -m "Archive ${tag}"
    git push
  fi
}

verify_tag_target() {
  local tag="$1"
  local expected_sha="$2"
  local actual_sha

  git fetch --tags --force >/dev/null
  actual_sha="$(git rev-list -n 1 "$tag" 2>/dev/null || true)"
  if [ -z "$actual_sha" ]; then
    echo "Expected release tag ${tag} does not exist." >&2
    exit 1
  fi
  if [ "$actual_sha" != "$expected_sha" ]; then
    echo "Release tag ${tag} points to ${actual_sha}, expected ${expected_sha}." >&2
    exit 1
  fi
}

publish_draft_if_needed() {
  local tag="$1"
  local is_draft

  is_draft="$(gh release view "$tag" --json isDraft --jq '.isDraft')"
  if [ "$is_draft" = "true" ]; then
    gh release edit "$tag" --draft=false
  fi
}

ensure_release_tag() {
  local tag="$1"
  local expected_sha="$2"

  git fetch --tags --force >/dev/null
  if git rev-parse -q --verify "refs/tags/${tag}" >/dev/null; then
    verify_tag_target "$tag" "$expected_sha"
    return
  fi

  git tag "$tag" "$expected_sha"
  git push origin "refs/tags/${tag}"
  verify_tag_target "$tag" "$expected_sha"
}

tag="$(read_manifest_field release.tag)"
title="$(read_manifest_field release.title)"
target_sha="$(read_manifest_field workflow.commit_sha)"
amd64_filename="$(artifact_filename_for_arch amd64)"
arm64_filename="$(artifact_filename_for_arch arm64)"

python3 scripts/release_guard.py validate-manifest --manifest "$manifest_path"

staged_assets="$tmpdir/new-assets"
mkdir -p "$staged_assets"

for path in "$amd64_artifact_path" "$arm64_artifact_path" "$amd64_inspection_path" "$arm64_inspection_path"; do
  if [ ! -f "$path" ]; then
    echo "Missing release input: $path" >&2
    exit 1
  fi
done

python3 scripts/release_guard.py verify-local-artifact \
  --manifest "$manifest_path" \
  --artifact "$amd64_artifact_path" \
  --inspection "$amd64_inspection_path"
python3 scripts/release_guard.py verify-local-artifact \
  --manifest "$manifest_path" \
  --artifact "$arm64_artifact_path" \
  --inspection "$arm64_inspection_path"

cp "$amd64_artifact_path" "$staged_assets/$amd64_filename"
cp "$arm64_artifact_path" "$staged_assets/$arm64_filename"
cp "$manifest_path" "$staged_assets/chatgpt-deb-manifest.json"
cp "$release_notes_path" "$staged_assets/release-notes.md"
python3 scripts/release_guard.py verify-assets \
  --manifest "$manifest_path" \
  --asset-dir "$staged_assets" \
  --require-manifest-asset \
  --release-notes "$release_notes_path"

if gh release view "$tag" >/dev/null 2>&1; then
  existing_assets="$tmpdir/existing-assets"
  mkdir -p "$existing_assets"
  gh release download "$tag" --dir "$existing_assets"
  python3 scripts/release_guard.py verify-assets \
    --manifest "$manifest_path" \
    --asset-dir "$existing_assets" \
    --require-manifest-asset \
    --release-notes "$release_notes_path"
  verify_tag_target "$tag" "$target_sha"
  publish_draft_if_needed "$tag"
  commit_manifest "$tag"
  echo "Release ${tag} already exists with verified assets; repository manifest is current."
  exit 0
fi

ensure_release_tag "$tag" "$target_sha"

gh release create "$tag" \
  "$staged_assets/$amd64_filename" \
  "$staged_assets/$arm64_filename" \
  "$staged_assets/chatgpt-deb-manifest.json" \
  "$staged_assets/release-notes.md" \
  --draft \
  --title "$title" \
  --notes-file "$release_notes_path"

verify_tag_target "$tag" "$target_sha"

published_assets="$tmpdir/published-assets"
mkdir -p "$published_assets"
gh release download "$tag" --dir "$published_assets"
python3 scripts/release_guard.py verify-assets \
  --manifest "$manifest_path" \
  --asset-dir "$published_assets" \
  --require-manifest-asset \
  --release-notes "$release_notes_path"

publish_draft_if_needed "$tag"
commit_manifest "$tag"
