from fastapi.testclient import TestClient

from app.api.health import health
from app.main import app


def test_health_reports_engine_separately_from_catalog_readiness() -> None:
    result = health()
    assert result.status == "ok"
    assert result.project == "coq"
    assert result.linguistic_contracts_approved is False
    assert result.conjugation_engine_available is True
    assert isinstance(result.production_catalog_ready, bool)


def test_health_http_contract_is_explicit() -> None:
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["project"] == "coq"
    assert payload["linguistic_contracts_approved"] is False
    assert payload["conjugation_engine_available"] is True
    assert isinstance(payload["production_catalog_ready"], bool)
