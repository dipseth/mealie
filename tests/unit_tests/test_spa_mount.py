"""
Tests for mount_spa and the DISABLE_FRONTEND setting (headless / API-only mode).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mealie.routes import spa


@pytest.fixture()
def spa_dir(tmp_path):
    """Temporary directory standing in for the built frontend."""
    (tmp_path / "index.html").write_text("<!DOCTYPE html><html><head></head><body>index</body></html>")
    (tmp_path / "404.html").write_text("<!DOCTYPE html><html><head></head><body>spa-shell</body></html>")
    return tmp_path


def _build_app(monkeypatch: pytest.MonkeyPatch, static_files: str, disable_frontend: bool) -> FastAPI:
    settings = getattr(spa, "__app_settings")
    patched = settings.model_copy(update={"STATIC_FILES": static_files, "DISABLE_FRONTEND": disable_frontend})
    monkeypatch.setattr(spa, "__app_settings", patched)

    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    spa.mount_spa(app)
    return app


def test_frontend_served_by_default(monkeypatch: pytest.MonkeyPatch, spa_dir):
    client = TestClient(_build_app(monkeypatch, str(spa_dir), disable_frontend=False))

    response = client.get("/some/client/route")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert client.get("/api/ping").json() == {"ok": True}


def test_disable_frontend_skips_spa(monkeypatch: pytest.MonkeyPatch, spa_dir):
    app = _build_app(monkeypatch, str(spa_dir), disable_frontend=True)
    client = TestClient(app)

    assert all(getattr(route, "name", None) != "spa" for route in app.routes)
    assert client.get("/").status_code == 404
    assert client.get("/some/client/route").status_code == 404
    assert client.get("/manifest.webmanifest").status_code == 404
    assert client.get("/g/home/r/some-recipe").status_code == 404


def test_disable_frontend_keeps_api(monkeypatch: pytest.MonkeyPatch, spa_dir):
    client = TestClient(_build_app(monkeypatch, str(spa_dir), disable_frontend=True))

    response = client.get("/api/ping")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
