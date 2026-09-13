from fastapi.testclient import TestClient
from app.main import app


def test_webhook_requires_shared_secret(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SHARED_SECRET", "super-secret")
    client = TestClient(app)
    resp = client.post(
        "/api/v1/webhooks/aprovacao-orcamento",
        json={"ordem_servico_id": 1, "aprovado": True},
    )
    assert resp.status_code == 401


def test_aprovacao_orcamento_webhook_aprova(monkeypatch):
    called = {}
    monkeypatch.setenv("WEBHOOK_SHARED_SECRET", "super-secret")

    def fake_aprovar(db, os_id):
        called["aprovar"] = os_id

    def fake_alterar_status(db, os_id, novo_status, observacao=None):
        called["alterar"] = (os_id, str(novo_status))

    monkeypatch.setattr(
        "app.services.ordem_servico_service.aprovar_orcamento", fake_aprovar
    )
    monkeypatch.setattr(
        "app.services.ordem_servico_service.alterar_status", fake_alterar_status
    )

    client = TestClient(app)
    headers = {"x-webhook-token": "super-secret"}
    resp = client.post(
        "/api/v1/webhooks/aprovacao-orcamento",
        json={"ordem_servico_id": 1, "aprovado": True, "iniciar_execucao": False},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "aprovado"
    assert called.get("aprovar") == 1


def test_aprovacao_orcamento_webhook_recusa(monkeypatch):
    called = {}
    monkeypatch.setenv("WEBHOOK_SHARED_SECRET", "super-secret")

    def fake_alterar_status(db, os_id, novo_status, observacao=None):
        called["alterar"] = (os_id, str(novo_status))

    monkeypatch.setattr(
        "app.services.ordem_servico_service.alterar_status", fake_alterar_status
    )

    client = TestClient(app)
    headers = {"x-webhook-token": "super-secret"}
    resp = client.post(
        "/api/v1/webhooks/aprovacao-orcamento",
        json={"ordem_servico_id": 2, "aprovado": False},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "recusado"
    assert called.get("alterar")[0] == 2


def test_email_status_webhook(monkeypatch):
    called = {}
    monkeypatch.setenv("WEBHOOK_SHARED_SECRET", "super-secret")

    def fake_alterar_status(db, os_id, novo_status, observacao=None):
        called["alterar"] = (os_id, str(novo_status), observacao)

    monkeypatch.setattr(
        "app.services.ordem_servico_service.alterar_status", fake_alterar_status
    )

    client = TestClient(app)
    headers = {"x-webhook-token": "super-secret"}
    resp = client.post(
        "/api/v1/webhooks/email-status",
        json={
            "ordem_servico_id": 3,
            "novo_status": "em_execucao",
            "observacao": "envio via email",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert called.get("alterar")[0] == 3
    # aceitar tanto o Enum como seu valor em string
    assert "em_execucao" in called.get("alterar")[1].lower()
