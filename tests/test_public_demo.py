from fastapi.testclient import TestClient

import app as service
from dataset import TOPICS


def test_public_demo_scores_without_creating_database(tmp_path, monkeypatch):
    path = tmp_path / "private.db"
    monkeypatch.setattr(service, "DB_PATH", path)
    monkeypatch.setattr(service, "PUBLIC_DEMO", True)
    topic = TOPICS[0]
    submission = dict(student="Public sample", title=topic["title"], question=topic["question"],
                      answer=topic["paraphrase"], reference=topic["reference"], concepts=topic["concepts"])
    with TestClient(service.app) as client:
        assert client.get("/api/config").json() == {"browser_history": True}
        response = client.post("/api/evaluate", json=submission)
        assert response.status_code == 201
        assert response.json()["score"] == 80.3
        assert response.headers["Cache-Control"] == "no-store"
        result_path = "/api/evaluations/" + response.json()["id"]
        assert client.get(result_path).status_code == 404
        assert client.delete(result_path).status_code == 404
        assert client.get("/api/evaluations").status_code == 404
        assert client.get("/api/export").status_code == 404
        assert client.post("/api/extract", files={"file": ("answer.txt", "Example answer text.")}).status_code == 200
    assert not path.exists()
