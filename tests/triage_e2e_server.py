"""Start the real API with isolated disposable stores for triage browser tests."""
from __future__ import annotations

import os
import json
import shutil
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    test_root = (root / "test-results" / "triage-e2e").resolve()
    raw = os.environ.get("TRIAGE_E2E_DB_DIR")
    if not raw:
        raise SystemExit("TRIAGE_E2E_DB_DIR is required")
    run_dir = Path(raw).resolve()
    if run_dir == test_root or test_root not in run_dir.parents:
        raise SystemExit("TRIAGE_E2E_DB_DIR must be a child of test-results/triage-e2e")
    run_dir.mkdir(parents=True, exist_ok=False)
    stores = {
        "AUTH_DB_PATH": "auth.db", "GLUCOSE_DB_PATH": "glucose.db",
        "VITALS_DB_PATH": "vitals.db", "MONITORING_DB_PATH": "monitoring.db",
        "TRACING_DB_PATH": "tracing.db", "LAB_DB_PATH": "labs.db",
        "LEARN_DB_PATH": "learn.db", "MEDICATION_DB_PATH": "medications.db",
        "CARE_DB_PATH": "care-workflows.db",
        "TRIAGE_EVENTS_PATH": "triage-events.jsonl",
        "TRIAGE_AUDIT_PATH": "red-flags.jsonl", "VOICE_PREFS_PATH": "voice-prefs.json",
    }
    for name, filename in stores.items():
        os.environ[name] = str(run_dir / filename)
    os.environ["MONITOR_SCHEDULER_DISABLE"] = "true"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from dotenv import load_dotenv
    load_dotenv(root / ".env")
    os.environ["FRONTEND_URL"] = os.environ.get("TRIAGE_E2E_FRONTEND_URL", "http://127.0.0.1:3108")
    live_rag = os.environ.get("TRIAGE_E2E_LIVE_RAG") == "1"
    # Live RAG is opt-in; ordinary triage tests never call NVIDIA.
    for _key in ("NVDIA_API_KEY", "NVDIA_API_KEY2", "NVDIA_API_KEY3",
                 "NVIDIA_API_KEY", "NVIDIA_API_KEY2", "NVIDIA_API_KEY3"):
        if not live_rag:
            os.environ[_key] = ""
    os.environ["COOKIE_SECURE"] = "false"
    os.environ["COOKIE_SAMESITE"] = "lax"

    if live_rag:
        manifest = json.loads((root / "src/shared/corpus_provenance.json").read_text(encoding="utf-8"))
        active = manifest["active_index"]
        source = root / active["index_dir"]
        target = run_dir / "index" / source.name
        shutil.copytree(source, target)
        active["index_dir"] = str(target)
        active["path"] = str(target / "verified_manifest.json")
        test_manifest = run_dir / "corpus_provenance.json"
        test_manifest.write_text(json.dumps(manifest), encoding="utf-8")
        os.environ["NVIDIA_PDF_DB_DIR"] = str(target.parent)
        # Relative memory stores stay in this disposable run, including reads.
        os.chdir(run_dir)

    from src.auth.db import create_user, init_auth_db
    from src.auth.security import hash_password

    init_auth_db()
    create_user("triage_nurse", None, hash_password("Nurse@12345"), None,
                "nurse", is_verified=True)
    create_user("live_admin", None, hash_password("TestAdmin@123"), None,
                "admin", is_verified=True)
    create_user("medication_doctor", None, hash_password("Doctor@12345"), None,
                "doctor", is_verified=True)
    create_user("other_medication_doctor", None, hash_password("Doctor@12345"), None,
                "doctor", is_verified=True)
    create_user("care_doctor", None, hash_password("Doctor@12345"), None,
                "doctor", is_verified=True)
    create_user("care_specialist", None, hash_password("Specialist@12345"), None,
                "specialist", is_verified=True)
    create_user("booking_receptionist", None, hash_password("Reception@12345"), None,
                "receptionist", is_verified=True)
    from src.api.main import app
    if live_rag:
        import src.shared.corpus_provenance
        for name, module in tuple(sys.modules.items()):
            if name.endswith("shared.corpus_provenance"):
                module.MANIFEST_PATH = test_manifest
                module._manifest.cache_clear()
        assert src.shared.corpus_provenance.validate_serving_index()["chunks"] == 452
    import uvicorn
    uvicorn.run(app, host="127.0.0.1",
                port=int(os.environ.get("TRIAGE_E2E_API_PORT", "8108")), log_level="warning")


if __name__ == "__main__":
    main()
