"""Run the synthetic glucose API pilot. CI artifact: test-results/feature-pilot/glucose.xml."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
NODE = "tests/test_api_diabetes.py::TestDiabetesAPI::test_glucose_110_roundtrip_and_ownership"
REPORT = ROOT / "test-results" / "feature-pilot" / "glucose.xml"


def main():
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        workspace = Path(temp)
        shutil.copytree(ROOT / "src", workspace / "src", ignore=shutil.ignore_patterns("__pycache__"))
        (workspace / "tests").mkdir()
        for name in ("tests/conftest.py", "tests/test_api_diabetes.py", "tests/__init__.py", "pyproject.toml"):
            shutil.copyfile(ROOT / name, workspace / name)
        # Corpus verification is a separate startup contract. This pilot runs without a clinical index.
        (workspace / "pilot_fixture.py").write_text(
            "import pytest\n"
            "@pytest.fixture(scope='session', autouse=True)\n"
            "def isolated_corpus():\n"
            "    from unittest.mock import patch\n"
            "    with patch('src.shared.corpus_provenance.validate_serving_index'):\n"
            "        yield\n",
            encoding="utf-8",
        )
        env = {key: os.environ[key] for key in ("PATH", "SystemRoot", "WINDIR", "COMSPEC", "LANG")
               if key in os.environ}
        env.update(TMP=temp, TEMP=temp, TMPDIR=temp, USERPROFILE=temp, HOME=temp, MONITOR_SCHEDULER_DISABLE="true",
                   PYTHON_DOTENV_DISABLED="1", PYTHONUTF8="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "pilot_fixture", NODE, "-q", f"--junitxml={REPORT}"],
            cwd=workspace, env=env, check=False,
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
