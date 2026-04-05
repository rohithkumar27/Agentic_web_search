from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_serves_ui() -> None:
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "Agentic Search Console" in html
    assert 'id="query"' in html
    assert 'id="resultTable"' in html
    assert 'id="drawer"' in html
