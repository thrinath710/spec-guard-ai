import pytest

from backend.app.core.config import get_settings


@pytest.fixture(autouse=True)
def _force_heuristic_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("USE_LLM", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
