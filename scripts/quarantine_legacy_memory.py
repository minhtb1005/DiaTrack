"""Classify and mark policy-blocked legacy memories without deleting content."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import chromadb

from src.shared.privacy import PrivacyError, POLICY_VERSION, sanitize

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "embeddings" / "memory_db"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="mark blocked rows in place; never deletes")
    args = parser.parse_args()
    collection = chromadb.PersistentClient(path=str(STORE)).get_collection("langchain")
    rows = collection.get(limit=collection.count(), include=["documents", "metadatas"])
    blocked: list[tuple[str, dict, str]] = []
    for row_id, document, metadata in zip(rows["ids"], rows["documents"], rows["metadatas"]):
        try:
            sanitize({"content": document, "metadata": metadata})
        except PrivacyError as exc:
            reason = str(exc).rsplit(":", 1)[-1]
            blocked.append((row_id, dict(metadata or {}), reason))
    already = sum(bool(metadata.get("privacy_quarantined")) for _, metadata, _ in blocked)
    if args.apply and blocked:
        timestamp = datetime.now(timezone.utc).isoformat()
        collection.update(
            ids=[row_id for row_id, _, _ in blocked],
            metadatas=[{**metadata, "privacy_quarantined": True,
                        "privacy_policy_version": POLICY_VERSION,
                        "privacy_quarantine_reason": reason,
                        "privacy_quarantined_at": metadata.get("privacy_quarantined_at", timestamp)}
                       for _, metadata, reason in blocked],
        )
    report = {
        "status": "APPLIED" if args.apply else "DRY_RUN",
        "store": "local_legacy",
        "records": collection.count(),
        "blocked": len(blocked),
        "already_quarantined": already,
        "newly_quarantined": len(blocked) - already if args.apply else 0,
        "documents_deleted": 0,
        "contains_owner_or_content": False,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
