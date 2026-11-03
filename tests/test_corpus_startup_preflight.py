from pathlib import Path

import pytest

from src.shared.corpus_provenance import validate_serving_index


def test_current_verified_index_passes_startup_preflight():
    result = validate_serving_index()
    assert result["chunks"] == 452
    assert result["sources"] == 4


def test_startup_preflight_rejects_missing_or_different_index(tmp_path: Path):
    with pytest.raises(RuntimeError, match="missing or does not match"):
        validate_serving_index(tmp_path)
