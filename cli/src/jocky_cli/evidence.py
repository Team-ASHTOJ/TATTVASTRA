"""Evidence commands: verify and manifest.

Both delegate to jockyc's existing `variant-info`, which reads a variant
manifest and, when given an artifact, recomputes its SHA-256 and rejects a
mismatch (E265). jocky performs no hashing and no signing of its own.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import compiler, report


def manifest(argv: list[str]) -> int:
    """Print a variant manifest through jockyc's own variant-info output."""
    source, _, present = compiler.source_and_options(argv, (), ("--json",), "manifest")
    arguments = ["variant-info", source]
    if "--json" in present:
        arguments.append("--json")
    return compiler.run_stream(arguments, Path.cwd())


def verify(argv: list[str]) -> int:
    """Verify stored integrity: artifact bytes against the manifest SHA-256.

    jockyc does the comparison. jocky reports its verdict and never substitutes
    a hash of its own. No signature is checked, because no local signing exists.
    """
    source, _, present = compiler.source_and_options(argv, (), ("--json",), "verify")
    artifact = Path(source).suffix != ".json"

    result = compiler.run_capture(["variant-info", source, "--json"], Path.cwd())
    if result.returncode != 0:
        message = compiler.failure_message(result, source)
        if "--json" in present:
            report.emit_json(
                {
                    "schema_version": "1.0.0",
                    "kind": "JockyVerify",
                    "source": source,
                    "command": "variant-info",
                    "verified": False,
                    "failure": message,
                }
            )
            return result.returncode
        print(message, file=sys.stderr)
        return result.returncode

    document = json.loads(result.stdout or "{}")
    if "--json" in present:
        report.emit_json(
            {
                "schema_version": "1.0.0",
                "kind": "JockyVerify",
                "source": source,
                "command": "variant-info",
                "checked": "artifact_sha256" if artifact else "manifest_document",
                "verified": True,
                "signature_checked": False,
                "manifest": document,
            }
        )
        return 0

    print(f"jocky verify — {source}")
    if artifact:
        report.field("verified", "PASS — artifact bytes match the manifest SHA-256")
        report.field("artifact hash", document.get("artifact_hash") or "-")
    else:
        report.field("verified", "PASS — manifest parsed and validated")
        report.note("no artifact bytes were supplied, so no digest was compared")
    report.field("variant id", document.get("variant_id") or "-")
    report.field(
        "semantic result",
        document.get("semantic_result_hash") or "not recorded in this manifest",
    )
    report.note("integrity only: local manifests are unsigned, so no signature is checked")
    return 0
