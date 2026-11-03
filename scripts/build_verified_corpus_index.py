"""Build a new index from vectors whose text is proven to occur in verified PDFs."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import chromadb
import fitz

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "src" / "shared" / "corpus_provenance.json"
OLD_INDEX = ROOT / "embeddings" / "pdf_db_nvidia" / "hybrid_section_semantic"
NEW_INDEX = ROOT / "embeddings" / "pdf_db_nvidia_verified_20261102" / "hybrid_section_semantic"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tokens(text: str) -> list[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold(), re.UNICODE)


def page_chunks(text: str, size: int = 350, overlap: int = 50) -> list[str]:
    words = text.split()
    return [" ".join(words[start:start + size]) for start in range(0, len(words), size - overlap)
            if words[start:start + size]]


def read_pages(path: Path) -> list[str]:
    with fitz.open(path) as pdf:
        return [page.get_text("text") for page in pdf]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=NEW_INDEX)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty index: {output}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    approved = {
        source_id: entry for source_id, entry in manifest["sources"].items()
        if entry.get("binary_match") and (entry.get("approved_for_external_send")
                                          or entry.get("eligible_for_next_index"))
    }
    page_text: dict[str, list[str]] = {}
    for source_id, entry in approved.items():
        path = ROOT / entry["path"]
        if sha256_file(path) != entry["sha256"]:
            raise SystemExit(f"source hash mismatch: {source_id}")
        page_text[source_id] = read_pages(path)

    accepted: list[dict] = []
    for source_id, pages in page_text.items():
        for page_number, page in enumerate(pages, 1):
            for chunk_index, document in enumerate(page_chunks(page)):
                content_hash = sha256_bytes(document.encode("utf-8"))
                accepted.append({
                    "id": f"verified:{source_id}:{page_number}:{chunk_index}:{content_hash}",
                    "document": document,
                    "metadata": {
                        "source_id": source_id,
                        "page_numbers": str(page_number),
                        "chunk_index": chunk_index,
                        "chunking_strategy": "verified_page",
                        "source_sha256": approved[source_id]["sha256"],
                        "content_sha256": content_hash,
                        "chunk_hash": content_hash,
                        "provenance_version": manifest["version"],
                        "verified_from_raw": True,
                    },
                })

    from src.shared.nvidia import NvidiaEmbeddings
    from src.shared.config import NVIDIA_EMBEDDING_MODEL
    from src.shared.privacy import verified_public_scope
    texts = [row["document"] for row in accepted]
    with verified_public_scope(texts):
        embeddings = NvidiaEmbeddings(NVIDIA_EMBEDDING_MODEL).embed_documents(texts, batch_size=32)
    for row, embedding in zip(accepted, embeddings):
        row["embedding"] = embedding

    output.mkdir(parents=True, exist_ok=False)
    collection = chromadb.PersistentClient(path=str(output)).get_or_create_collection("langchain")
    for start in range(0, len(accepted), 64):
        batch = accepted[start:start + 64]
        collection.add(
            ids=[row["id"] for row in batch],
            documents=[row["document"] for row in batch],
            metadatas=[row["metadata"] for row in batch],
            embeddings=[row["embedding"] for row in batch],
        )
    sidecar = {
        "version": manifest["version"],
        "chunks": [{"content_sha256": row["metadata"]["content_sha256"],
                    "source_id": row["metadata"]["source_id"],
                    "page_numbers": row["metadata"]["page_numbers"]}
                   for row in accepted],
    }
    sidecar_path = output / "verified_manifest.json"
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": "PASSED", "chunks": collection.count(),
                      "sources": sorted(approved), "output": str(output),
                      "sidecar_sha256": sha256_file(sidecar_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
