"""Independently verify every clean-index chunk against its raw PDF page."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import chromadb
import fitz

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "embeddings" / "pdf_db_nvidia_verified_20261102" / "hybrid_section_semantic"
MANIFEST = ROOT / "src" / "shared" / "corpus_provenance.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def page_chunks(text: str, size: int = 350, overlap: int = 50) -> list[str]:
    words = text.split()
    return [" ".join(words[start:start + size]) for start in range(0, len(words), size - overlap)
            if words[start:start + size]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=INDEX)
    parser.add_argument("--include-eligible", action="store_true")
    args = parser.parse_args()
    index = args.index.resolve()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    approved = {key: value for key, value in manifest["sources"].items()
                if value.get("binary_match") and (value.get("approved_for_external_send")
                                                   or (args.include_eligible
                                                       and value.get("eligible_for_next_index")))}
    expected = set()
    source_integrity = {}
    for source_id, entry in approved.items():
        path = ROOT / entry["path"]
        source_integrity[source_id] = digest(path) == entry["sha256"]
        with fitz.open(path) as pdf:
            for page_number, page in enumerate(pdf, 1):
                for chunk in page_chunks(page.get_text("text")):
                    expected.add((source_id, str(page_number), hashlib.sha256(chunk.encode()).hexdigest()))

    collection = chromadb.PersistentClient(path=str(index)).get_collection("langchain")
    rows = collection.get(limit=collection.count(), include=["documents", "metadatas", "embeddings"])
    actual, invalid, dimensions = set(), 0, set()
    for document, metadata, embedding in zip(rows["documents"], rows["metadatas"], rows["embeddings"]):
        content_hash = hashlib.sha256(document.encode()).hexdigest()
        record = (metadata.get("source_id"), metadata.get("page_numbers"), content_hash)
        actual.add(record)
        dimensions.add(len(embedding))
        if (record not in expected or metadata.get("content_sha256") != content_hash
                or metadata.get("chunk_hash") != content_hash
                or metadata.get("source_sha256") != approved.get(record[0], {}).get("sha256")
                or metadata.get("verified_from_raw") is not True):
            invalid += 1
    sidecar = index / "verified_manifest.json"
    sidecar_rows = json.loads(sidecar.read_text(encoding="utf-8"))["chunks"]
    sidecar_set = {(row["source_id"], row["page_numbers"], row["content_sha256"])
                   for row in sidecar_rows}
    report = {
        "status": "PASSED" if not invalid and actual == expected == sidecar_set and all(source_integrity.values()) else "FAILED",
        "chunks": len(actual), "invalid_chunks": invalid, "embedding_dimensions": sorted(dimensions),
        "source_integrity": source_integrity, "expected_equals_index": actual == expected,
        "sidecar_equals_index": sidecar_set == actual, "sidecar_sha256": digest(sidecar),
        "contains_document_text": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
