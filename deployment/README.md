# Verified RAG deployment assets

`verified-rag-assets-20261102.zip` is a local/release artifact that is intentionally not tracked by Git. It contains the clean 452-chunk Chroma index and the four hash-verified source PDFs required by startup preflight. SHA-256:

`eca27169aa713db004dd2247e35fefdd54fa4289c868fa9916b508d1e4acf7e6`

After obtaining the archive through the controlled deployment channel, place it in `deployment/`. From the repository root, verify it, extract it without changing paths, and run the preflight:

```powershell
(Get-FileHash deployment\verified-rag-assets-20261102.zip -Algorithm SHA256).Hash.ToLower()
tar.exe -xf deployment\verified-rag-assets-20261102.zip
$env:NVIDIA_PDF_DB_DIR = "embeddings/pdf_db_nvidia_verified_20261102"
.\.venv\Scripts\python.exe -c "from src.shared.corpus_provenance import validate_serving_index; print(validate_serving_index())"
```

The API performs the same validation during startup and refuses to run when the configured directory, sidecar hash, source hashes or Chroma rows differ. Rebuild only with `scripts/build_verified_corpus_index.py` into a new empty versioned directory, then audit it before changing `src/shared/corpus_provenance.json`.
