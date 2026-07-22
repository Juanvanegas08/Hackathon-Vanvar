"""API tests for lead endpoints."""

from uuid import uuid4

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "CasaLista" in body["service"]


def test_create_and_get_lead(client: TestClient) -> None:
    create = client.post(
        "/api/v1/leads",
        json={
            "nombre": "Ana Pérez",
            "telefono": "3001234567",
            "correo": "ana@example.com",
            "canal_origen": "whatsapp",
            "consentimiento": True,
            "afiliado": True,
        },
    )
    assert create.status_code == 201
    lead = create.json()
    lead_id = lead["id"]
    assert lead["nombre"] == "Ana Pérez"
    assert lead["afiliado"] is True

    get_response = client.get(f"/api/v1/leads/{lead_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == lead_id


def test_partial_update_keeps_existing_values(client: TestClient) -> None:
    create = client.post(
        "/api/v1/leads",
        json={"nombre": "Carlos", "afiliado": True, "salario_mensual": 2500000},
    )
    lead_id = create.json()["id"]

    patch = client.patch(
        f"/api/v1/leads/{lead_id}",
        json={"ahorro": 18000000},
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["nombre"] == "Carlos"
    assert body["afiliado"] is True
    assert body["salario_mensual"] == 2500000
    assert body["ahorro"] == 18000000


def test_next_question_evaluate_and_summary(client: TestClient) -> None:
    create = client.post(
        "/api/v1/leads",
        json={"consentimiento": True},
    )
    lead_id = create.json()["id"]

    question = client.get(f"/api/v1/leads/{lead_id}/next-question")
    assert question.status_code == 200
    assert question.json()["completed"] is False
    assert question.json()["next_question"]["field"] == "afiliado"

    client.patch(
        f"/api/v1/leads/{lead_id}",
        json={
            "afiliado": True,
            "salario_mensual": 2500000,
            "ingreso_hogar": 4200000,
            "ahorro": 18000000,
            "obligaciones_mensuales": 500000,
            "tiene_vivienda": False,
            "personas_hogar": 3,
            "personas_a_cargo": 1,
            "situacion_crediticia": "al_dia",
            "ubicacion_deseada": "Bogotá",
            "plazo_compra": "6_meses",
        },
    )

    evaluate = client.post(f"/api/v1/leads/{lead_id}/evaluate")
    assert evaluate.status_code == 200
    eval_body = evaluate.json()
    assert 0 <= eval_body["readiness_score"] <= 100
    assert "disclaimer" in eval_body

    summary = client.get(f"/api/v1/leads/{lead_id}/summary")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["lead_id"] == lead_id
    assert summary_body["recommended_projects"] == []
    assert "no constituye" in summary_body["disclaimer"].lower()


def test_missing_lead_returns_404(client: TestClient) -> None:
    missing_id = uuid4()
    response = client.get(f"/api/v1/leads/{missing_id}")
    assert response.status_code == 404


def test_validation_error_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/leads",
        json={"salario_mensual": -10},
    )
    assert response.status_code == 422


def test_affiliation_category_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/v1/evaluation/affiliation-category",
        json={
            "afiliado": True,
            "salario_mensual": 1750000,
            "afiliacion_confirmada": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["categoria"] == "A"
    assert body["requiere_confirmacion"] is True
    assert body["salario_en_smmlv"] == 1.75


def test_delete_lead(client: TestClient) -> None:
    create = client.post("/api/v1/leads", json={"nombre": "Temporal"})
    lead_id = create.json()["id"]
    delete = client.delete(f"/api/v1/leads/{lead_id}")
    assert delete.status_code == 204
    assert client.get(f"/api/v1/leads/{lead_id}").status_code == 404
