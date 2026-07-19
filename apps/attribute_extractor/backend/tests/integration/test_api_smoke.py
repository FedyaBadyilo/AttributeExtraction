from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = APP_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import smoke_api_ui as smoke  # noqa: E402


def _backend_up() -> bool:
    try:
        smoke.request(smoke.API, "GET", "/health", expect=200)
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def require_backend():
    if not _backend_up():
        pytest.skip(f"Backend not reachable at {smoke.API}")


@pytest.mark.integration
def test_api_smoke_flow(require_backend):
    report = smoke.Report()
    smoke.run_suite(smoke.API, "api", report)
    failed = report.failed
    assert not failed, "; ".join(f"{c.name}: {c.detail}" for c in failed)


@pytest.mark.integration
def test_ui_proxy_smoke_flow(require_backend):
    report = smoke.Report()
    smoke.run_suite(smoke.PROXY, "ui-proxy", report, with_ui_assets=True)
    failed = report.failed
    assert not failed, "; ".join(f"{c.name}: {c.detail}" for c in failed)
