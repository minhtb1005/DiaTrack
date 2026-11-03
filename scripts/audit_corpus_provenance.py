"""Audit the active corpus without emitting document text."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "src" / "shared" / "corpus_provenance.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = {"active_index": manifest["active_index"], **manifest["sources"], **manifest["tools"]}
    integrity = {
        key: sha256(ROOT / entry["path"]) == entry["sha256"]
        for key, entry in entries.items()
    }
    index_path = ROOT / manifest["active_index"]["index_dir"] / "chroma.sqlite3"
    with sqlite3.connect(f"file:{index_path.as_posix()}?mode=ro", uri=True) as db:
        source_counts = dict(db.execute(
            "SELECT string_value, COUNT(*) FROM embedding_metadata "
            "WHERE key = 'source_id' GROUP BY string_value ORDER BY string_value"
        ))
        chunk_count = db.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]

    sources = manifest["sources"]
    classes = Counter()
    for source_id, count in source_counts.items():
        entry = sources.get(source_id)
        if not entry:
            classes["unknown_or_out_of_scope_chunks"] += count
        elif entry.get("approved_for_external_send") and entry.get("binary_match"):
            classes["approved_chunks"] += count
        else:
            classes["unverified_chunks"] += count

    report = {
        "manifest_version": manifest["version"],
        "integrity": integrity,
        "index": {
            "chunk_count": chunk_count,
            "source_id_count": len(source_counts),
            "classification": dict(classes),
            "source_counts": source_counts,
        },
        "runtime_policy": "deny any context whose source is absent, unapproved, binary-unverified, or hash-mismatched",
        "contains_document_text": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    approved = classes["approved_chunks"]
    return 0 if all(integrity.values()) and approved > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
