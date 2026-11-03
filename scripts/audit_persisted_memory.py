"""Audit persisted vector memories without printing owners or content."""
from __future__ import annotations

import json
from pathlib import Path

import chromadb

from src.shared.privacy import PrivacyError, sanitize

ROOT = Path(__file__).resolve().parents[1]
STORES = {
    "local_legacy": ROOT / "embeddings" / "memory_db",
    "nvidia_active": ROOT / "embeddings" / "memory_db_nvidia",
    "openai_legacy": ROOT / "embeddings" / "memory_db_openai",
}


def main() -> int:
    report = {}
    for name, path in STORES.items():
        collection = chromadb.PersistentClient(path=str(path)).get_collection("langchain")
        rows = collection.get(limit=collection.count(), include=["documents", "metadatas"])
        missing_owner = blocked = 0
        for document, metadata in zip(rows["documents"], rows["metadatas"]):
            missing_owner += not bool((metadata or {}).get("user_id"))
            try:
                sanitize({"content": document, "metadata": metadata})
            except PrivacyError:
                blocked += 1
        report[name] = {"records": collection.count(), "missing_owner": missing_owner,
                        "blocked_by_current_policy": blocked,
                        "serving": name == "nvidia_active"}
    report["status"] = "PASSED" if (report["nvidia_active"]["missing_owner"] == 0
                                      and report["nvidia_active"]["blocked_by_current_policy"] == 0) else "FAILED"
    report["contains_owner_or_content"] = False
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
