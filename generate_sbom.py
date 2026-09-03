#!/usr/bin/env python
"""
Builds sbom.json (SPDX 2.3) from requirements.lock.txt.

Replaces the old workflow of manually exporting sbom.json from GitHub's
Dependency Graph UI (Insights -> Dependency Graph -> Export SBOM), which
requires a browser and only resolves fuzzy "~>" version ranges. This reads
the exact pins already maintained in requirements.lock.txt, so the SBOM
stays in sync with what's actually installed with a single local command.

Usage:
    python3 generate_sbom.py

This also regenerates sbom.dot via pyspdxtools (requires the one-off
tooling dependencies in requirements-sbom.txt — spdx-tools, networkx,
pygraphviz — and the system `graphviz`/`graphviz-dev` packages that
pygraphviz builds against). To finish with an .svg:
    dot -Tsvg sbom.dot -o sbom.svg
"""

import datetime
import json
import re
import subprocess
import uuid

LOCK_FILE = "requirements.lock.txt"
SBOM_FILE = "sbom.json"
PROJECT_NAME = "com.github.rikosintie/Discovery"
PROJECT_SPDX_ID = "SPDXRef-com.github.rikosintie-Discovery"


def read_pinned_packages(lock_file: str) -> list[tuple[str, str]]:
    """
    Parses "name==version" lines from a pip lock file, skipping blank
    lines and comments.
    """
    packages = []
    with open(lock_file, encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            match = re.match(r"^([A-Za-z0-9._-]+)==([A-Za-z0-9._+!-]+)$", line)
            if not match:
                continue
            packages.append((match.group(1), match.group(2)))
    return packages


def spdx_id_for(name: str) -> str:
    """SPDX identifiers only allow letters, digits, '.', and '-'."""
    safe = re.sub(r"[^A-Za-z0-9.-]", "-", name)
    return f"SPDXRef-pip-{safe}"


def build_sbom(packages: list[tuple[str, str]]) -> dict:
    document_namespace = (
        f"https://github.com/rikosintie/Discovery/sbom-{uuid.uuid4().hex[:16]}"
    )
    created = (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    root_package = {
        "SPDXID": PROJECT_SPDX_ID,
        "name": PROJECT_NAME,
        "versionInfo": "",
        "downloadLocation": "git+https://github.com/rikosintie/Discovery",
        "licenseDeclared": "Unlicense",
        "filesAnalyzed": False,
        "supplier": "NOASSERTION",
        "externalRefs": [
            {
                "referenceCategory": "PACKAGE-MANAGER",
                "referenceType": "purl",
                "referenceLocator": "pkg:github/rikosintie/Discovery",
            }
        ],
    }

    dep_packages = []
    relationships = []
    for name, version in packages:
        pkg_id = spdx_id_for(name)
        dep_packages.append(
            {
                "SPDXID": pkg_id,
                "name": f"pip:{name}",
                "versionInfo": version,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "supplier": "NOASSERTION",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": f"pkg:pypi/{name}@{version}",
                    }
                ],
            }
        )
        relationships.append(
            {
                "relationshipType": "DEPENDS_ON",
                "spdxElementId": PROJECT_SPDX_ID,
                "relatedSpdxElement": pkg_id,
            }
        )

    return {
        "SPDXID": "SPDXRef-DOCUMENT",
        "spdxVersion": "SPDX-2.3",
        "creationInfo": {
            "created": created,
            "creators": ["Tool: generate_sbom.py"],
            "comment": (
                "Generated locally from requirements.lock.txt — every "
                "version below is an exact pin, not a resolved range."
            ),
        },
        "name": PROJECT_NAME,
        "dataLicense": "CC0-1.0",
        "documentDescribes": [PROJECT_SPDX_ID],
        "documentNamespace": document_namespace,
        "packages": [root_package] + dep_packages,
        "relationships": relationships,
    }


def main() -> None:
    packages = read_pinned_packages(LOCK_FILE)
    if not packages:
        raise SystemExit(f"No pinned packages found in {LOCK_FILE}")
    sbom = build_sbom(packages)
    with open(SBOM_FILE, "w", encoding="utf-8") as f:
        json.dump(sbom, f, separators=(",", ":"))
    print(f"Wrote {len(packages)} packages to {SBOM_FILE}")

    try:
        subprocess.run(
            ["pyspdxtools", "-i", SBOM_FILE, "--graph", "-o", "sbom.dot"],
            check=True,
        )
    except FileNotFoundError:
        print(
            "pyspdxtools not found — install requirements-sbom.txt to "
            "validate and regenerate sbom.dot"
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"pyspdxtools validation failed: {exc}") from exc


if __name__ == "__main__":
    main()
