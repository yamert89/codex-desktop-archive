#!/usr/bin/env python3
"""Inspect a Debian package without installing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


EXPECTED_PACKAGE = "chatgpt"
EXPECTED_ARCHITECTURES = {"amd64", "arm64"}
CONTROL_FIELDS = [
    "Package",
    "Version",
    "Architecture",
    "Maintainer",
    "Installed-Size",
    "Depends",
    "Recommends",
    "Section",
    "Priority",
    "Homepage",
    "Description",
]
MAINTAINER_SCRIPT_NAMES = ["preinst", "postinst", "prerm", "postrm"]
ALLOWED_EXECUTABLE_PREFIXES = (
    "./opt/",
    "./usr/bin/",
    "./usr/lib/",
    "./usr/libexec/",
    "./usr/share/",
)
SUSPICIOUS_SCRIPT_PATTERNS = [
    r"\bcurl\b",
    r"\bwget\b",
    r"\bnc\b",
    r"\bnetcat\b",
    r"\bbase64\s+-d\b",
    r"\beval\b",
]


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, text=True, capture_output=True)


def _require_tool(name: str) -> None:
    result = _run(["sh", "-c", f"command -v {name}"])
    if result.returncode != 0:
        raise SystemExit(f"Required tool not found: {name}")


def _field(deb_path: Path, field: str) -> str | None:
    result = _run(["dpkg-deb", "-f", str(deb_path), field])
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _control_fields(deb_path: Path) -> dict[str, str]:
    return {
        field.lower().replace("-", "_"): value
        for field in CONTROL_FIELDS
        if (value := _field(deb_path, field)) is not None
    }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _maintainer_scripts(deb_path: Path) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory() as tmp:
        control_dir = Path(tmp) / "control"
        control_dir.mkdir()
        result = _run(["dpkg-deb", "-e", str(deb_path), str(control_dir)])
        if result.returncode != 0:
            raise SystemExit(result.stderr.strip() or "dpkg-deb failed to extract control archive")

        scripts = []
        for name in MAINTAINER_SCRIPT_NAMES:
            script_path = control_dir / name
            if not script_path.exists():
                continue
            data = script_path.read_bytes()
            text = data.decode("utf-8", errors="replace")
            suspicious_patterns = [
                pattern
                for pattern in SUSPICIOUS_SCRIPT_PATTERNS
                if re.search(pattern, text)
            ]
            scripts.append(
                {
                    "name": name,
                    "size": len(data),
                    "sha256": _sha256_bytes(data),
                    "executable": os.access(script_path, os.X_OK),
                    "suspicious_patterns": suspicious_patterns,
                }
            )
        return scripts


def _payload_inventory(deb_path: Path) -> dict[str, Any]:
    result = _run(["dpkg-deb", "-c", str(deb_path)])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "dpkg-deb failed to list package contents")

    entries = []
    executable_payloads = []
    unexpected_executable_payloads = []
    for raw_line in result.stdout.splitlines():
        parts = raw_line.split(maxsplit=5)
        if len(parts) < 6:
            continue
        mode, owner_group, size, date, time, path = parts
        entry = {
            "mode": mode,
            "owner_group": owner_group,
            "size": int(size),
            "date": date,
            "time": time,
            "path": path,
        }
        entries.append(entry)
        is_executable = "x" in mode[:10]
        if is_executable and not mode.startswith("d"):
            executable_payloads.append(path)
            if not path.startswith(ALLOWED_EXECUTABLE_PREFIXES):
                unexpected_executable_payloads.append(path)

    return {
        "file_count": len(entries),
        "entries": entries,
        "executable_payloads": sorted(executable_payloads),
        "unexpected_executable_payloads": sorted(unexpected_executable_payloads),
    }


def inspect_deb(deb_path: Path, expected_architecture: str | None) -> dict[str, Any]:
    _require_tool("dpkg-deb")
    control = _control_fields(deb_path)
    payload = _payload_inventory(deb_path)
    maintainer_scripts = _maintainer_scripts(deb_path)

    package_name = control.get("package")
    architecture = control.get("architecture")
    version = control.get("version")
    expected_arch = expected_architecture or architecture
    checks = {
        "dpkg_deb_control_read": bool(control),
        "dpkg_deb_payload_list": payload["file_count"] > 0,
        "expected_package": package_name == EXPECTED_PACKAGE,
        "expected_architecture": architecture == expected_arch and architecture in EXPECTED_ARCHITECTURES,
        "version_present": bool(version),
        "maintainer_present": bool(control.get("maintainer")),
        "control_scripts_inspected": True,
        "no_suspicious_maintainer_scripts": not any(
            script["suspicious_patterns"] for script in maintainer_scripts
        ),
        "no_unexpected_executable_payloads": not payload["unexpected_executable_payloads"],
    }

    return {
        "platform": "linux",
        "classification": "full-installer",
        "format": "deb",
        "architecture": architecture,
        "package": {
            "name": package_name,
            "version": version,
            "architecture": architecture,
            "maintainer": control.get("maintainer"),
            "installed_size": control.get("installed_size"),
            "depends": control.get("depends"),
            "recommends": control.get("recommends"),
            "section": control.get("section"),
            "priority": control.get("priority"),
            "homepage": control.get("homepage"),
            "description": control.get("description"),
            "control_fields": control,
        },
        "deb": {
            "payload": payload,
            "maintainer_scripts": maintainer_scripts,
        },
        "verification": {
            "passed": all(checks.values()),
            "expected_package": EXPECTED_PACKAGE,
            "expected_architecture": expected_arch,
            "checks": checks,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a Linux DEB package without installing it.")
    parser.add_argument("deb", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--architecture", choices=sorted(EXPECTED_ARCHITECTURES))
    args = parser.parse_args()

    result = inspect_deb(args.deb, args.architecture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not result["verification"]["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
