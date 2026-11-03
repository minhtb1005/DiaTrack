"""Fail-closed provenance checks for material added to outbound RAG prompts."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from src.shared.privacy import PrivacyError

BASE_DIR = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path(__file__).with_name("corpus_provenance.json")
_PRIVATE_MEMORY = {"short_term_memory", "episodic_memory", "long_term_memory"}


@lru_cache(maxsize=1)
def _manifest() -> dict:
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise PrivacyError("provenance_manifest_unavailable") from exc


@lru_cache(maxsize=32)
def _sha256(relative_path: str, size: int, mtime_ns: int) -> str:
    del size, mtime_ns
    digest = hashlib.sha256()
    with (BASE_DIR / relative_path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verified_file(entry: dict) -> bool:
    relative = entry.get("path")
    expected = entry.get("sha256")
    if not isinstance(relative, str) or not isinstance(expected, str):
        return False
    path = BASE_DIR / relative
    try:
        stat = path.stat()
        return _sha256(relative, stat.st_size, stat.st_mtime_ns) == expected.lower()
    except OSError:
        return False


@lru_cache(maxsize=1)
def _verified_public_chunks() -> frozenset[tuple[str, str]]:
    index = _manifest().get("active_index", {})
    if not _verified_file(index):
        raise PrivacyError("corpus_index_integrity_failed")
    try:
        rows = json.loads((BASE_DIR / index["path"]).read_text(encoding="utf-8"))["chunks"]
        return frozenset((row["source_id"], row["content_sha256"]) for row in rows)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise PrivacyError("corpus_index_manifest_invalid") from exc


def validate_context_provenance(contexts) -> None:
    """Reject the whole request when any context lacks an approved, intact origin."""
    manifest = _manifest()
    index = manifest.get("active_index", {})
    if not _verified_file(index):
        raise PrivacyError("corpus_index_integrity_failed")
    verified_chunks = _verified_public_chunks()
    sources = manifest.get("sources", {})
    tools = manifest.get("tools", {})
    for context in contexts:
        source_id = getattr(context, "source_id", None)
        if source_id in _PRIVATE_MEMORY:
            continue
        entry = tools.get(source_id) or sources.get(source_id)
        if not entry or not entry.get("approved_for_external_send"):
            raise PrivacyError("corpus_provenance_unapproved")
        if source_id in sources and not entry.get("binary_match"):
            raise PrivacyError("corpus_binary_unverified")
        if not _verified_file(entry):
            raise PrivacyError("corpus_source_integrity_failed")
        if source_id in sources:
            content = getattr(context, "content", "")
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if getattr(context, "chunk_hash", None) != content_hash:
                raise PrivacyError("corpus_chunk_hash_mismatch")
            if (source_id, content_hash) not in verified_chunks:
                raise PrivacyError("corpus_chunk_not_verified")


def validate_serving_index(index_root: Path | None = None, strategy: str | None = None) -> dict:
    """Fail startup unless config, sidecar, sources and Chroma rows describe one index."""
    import chromadb
    from src.shared.config import DEFAULT_CHUNK_STRATEGY, NVIDIA_PDF_DB_DIR

    manifest = _manifest()
    active = manifest.get("active_index", {})
    root = Path(index_root or NVIDIA_PDF_DB_DIR).resolve()
    selected = (root / (strategy or DEFAULT_CHUNK_STRATEGY)).resolve()
    expected = (BASE_DIR / active.get("index_dir", "")).resolve()
    if selected != expected or not selected.is_dir():
        raise RuntimeError("verified index directory is missing or does not match the manifest")
    if not _verified_file(active):
        raise RuntimeError("verified index sidecar hash mismatch")

    sidecar = json.loads((BASE_DIR / active["path"]).read_text(encoding="utf-8"))
    expected_rows = {(row["source_id"], str(row["page_numbers"]), row["content_sha256"])
                     for row in sidecar["chunks"]}
    if len(expected_rows) != len(sidecar["chunks"]):
        raise RuntimeError("verified index sidecar contains duplicate rows")
    sources = manifest.get("sources", {})
    for source_id, _, _ in expected_rows:
        entry = sources.get(source_id, {})
        if not entry.get("approved_for_external_send") or not entry.get("binary_match") or not _verified_file(entry):
            raise RuntimeError(f"verified source mismatch: {source_id}")

    collection = chromadb.PersistentClient(path=str(selected)).get_collection("langchain")
    rows = collection.get(limit=collection.count(), include=["documents", "metadatas"])
    actual_rows = set()
    for document, metadata in zip(rows["documents"], rows["metadatas"]):
        content_hash = hashlib.sha256(document.encode("utf-8")).hexdigest()
        source_id = metadata.get("source_id")
        record = (source_id, str(metadata.get("page_numbers")), content_hash)
        if (metadata.get("content_sha256") != content_hash
                or metadata.get("chunk_hash") != content_hash
                or metadata.get("source_sha256") != sources.get(source_id, {}).get("sha256")
                or metadata.get("verified_from_raw") is not True):
            raise RuntimeError("verified index row metadata mismatch")
        actual_rows.add(record)
    if collection.count() != len(expected_rows) or actual_rows != expected_rows:
        raise RuntimeError("verified index rows do not match the sidecar")
    return {"chunks": len(actual_rows), "sources": len({row[0] for row in actual_rows}),
            "sidecar_sha256": active["sha256"]}
