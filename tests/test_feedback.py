"""F15 回归测试：反馈目标必须存在；正反馈要求高评分 + 判定正确；重复提交收敛为一行。"""

from fastapi.testclient import TestClient


def _create_incident_with_logs(client: TestClient, service_name: str) -> dict:
    service = client.post("/services", json={"name": service_name}).json()
    for message in [
        "DBConnectionTimeout while connecting to postgres",
        "Order creation failed because database is unavailable",
    ]:
        client.post(
            "/logs",
            json={"service_id": service["id"], "level": "ERROR", "message": message},
        )
    return client.post(
        "/incidents",
        json={"service_id": service["id"], "title": f"{service_name} incident"},
    ).json()


def _analyze(client: TestClient, incident_id: int) -> dict:
    response = client.post(f"/incidents/{incident_id}/analyze")
    assert response.status_code == 201
    return response.json()


def test_feedback_on_missing_analysis_returns_404(client: TestClient):
    response = client.post(
        "/analysis/999999/feedback",
        json={"rating": 5, "is_diagnosis_correct": True},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_feedback_upsert_updates_existing_row(client: TestClient):
    incident = _create_incident_with_logs(client, "fb-upsert-service")
    analysis = _analyze(client, incident["id"])

    first = client.post(
        f"/analysis/{analysis['id']}/feedback",
        json={"rating": 4, "is_diagnosis_correct": True, "comment": "first"},
    )
    assert first.status_code == 201
    second = client.post(
        f"/analysis/{analysis['id']}/feedback",
        json={"rating": 5, "is_diagnosis_correct": False, "comment": "second"},
    )
    assert second.status_code == 201

    fetched = client.get(f"/analysis/{analysis['id']}/feedback").json()
    # 重复提交收敛为同一行，值被更新
    assert fetched["id"] == first.json()["id"]
    assert fetched["rating"] == 5
    assert fetched["is_diagnosis_correct"] is False
    assert fetched["comment"] == "second"


def test_positive_feedback_requires_correctness(client: TestClient):
    correct_analysis = _analyze(
        client, _create_incident_with_logs(client, "fb-correct-service")["id"]
    )
    incorrect_analysis = _analyze(
        client, _create_incident_with_logs(client, "fb-incorrect-service")["id"]
    )

    client.post(
        f"/analysis/{correct_analysis['id']}/feedback",
        json={"rating": 5, "is_diagnosis_correct": True},
    )
    # 高评分但判定错误：不得进入正反馈清单
    client.post(
        f"/analysis/{incorrect_analysis['id']}/feedback",
        json={"rating": 5, "is_diagnosis_correct": False},
    )

    positive = client.get("/feedback").json()

    assert [item["analysis_run_id"] for item in positive] == [correct_analysis["id"]]


def test_positive_feedback_respects_min_rating(client: TestClient):
    analysis = _analyze(
        client, _create_incident_with_logs(client, "fb-minrating-service")["id"]
    )
    client.post(
        f"/analysis/{analysis['id']}/feedback",
        json={"rating": 3, "is_diagnosis_correct": True},
    )

    assert client.get("/feedback").json() == []
    assert len(client.get("/feedback?min_rating=3").json()) == 1
