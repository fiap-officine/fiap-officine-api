from unittest.mock import patch


class TestServicosAPI:
    def test_criar_servico(self, client, auth_headers, servico_data):
        response = client.post(
            "/api/v1/servicos/", json=servico_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Troca de Óleo"
        assert float(data["preco"]) == 150.00

    def test_listar_servicos(self, client, auth_headers, servico_data):
        client.post("/api/v1/servicos/", json=servico_data, headers=auth_headers)
        response = client.get("/api/v1/servicos/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_buscar_servico(self, client, auth_headers, servico_data):
        create_resp = client.post(
            "/api/v1/servicos/", json=servico_data, headers=auth_headers
        )
        servico_id = create_resp.json()["id"]
        response = client.get(f"/api/v1/servicos/{servico_id}", headers=auth_headers)
        assert response.status_code == 200

    def test_atualizar_servico(self, client, auth_headers, servico_data):
        create_resp = client.post(
            "/api/v1/servicos/", json=servico_data, headers=auth_headers
        )
        servico_id = create_resp.json()["id"]
        response = client.put(
            f"/api/v1/servicos/{servico_id}",
            json={"preco": 200.00},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert float(response.json()["preco"]) == 200.00

    def test_desativar_servico(self, client, auth_headers, servico_data):
        create_resp = client.post(
            "/api/v1/servicos/", json=servico_data, headers=auth_headers
        )
        servico_id = create_resp.json()["id"]
        response = client.patch(
            f"/api/v1/servicos/{servico_id}/desativar",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["ativo"] is False

    def test_ativar_servico(self, client, auth_headers, servico_data):
        create_resp = client.post(
            "/api/v1/servicos/", json=servico_data, headers=auth_headers
        )
        servico_id = create_resp.json()["id"]
        client.patch(f"/api/v1/servicos/{servico_id}/desativar", headers=auth_headers)
        response = client.patch(
            f"/api/v1/servicos/{servico_id}/ativar", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["ativo"] is True


class TestPecasAPI:
    def test_criar_peca(self, client, auth_headers, peca_data):
        response = client.post("/api/v1/pecas/", json=peca_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Filtro de Óleo"
        assert data["quantidade_estoque"] == 50

    def test_listar_pecas(self, client, auth_headers, peca_data):
        client.post("/api/v1/pecas/", json=peca_data, headers=auth_headers)
        response = client.get("/api/v1/pecas/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_atualizar_estoque(self, client, auth_headers, peca_data):
        create_resp = client.post(
            "/api/v1/pecas/", json=peca_data, headers=auth_headers
        )
        peca_id = create_resp.json()["id"]
        response = client.put(
            f"/api/v1/pecas/{peca_id}",
            json={"quantidade_estoque": 100},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["quantidade_estoque"] == 100

    def test_desativar_peca(self, client, auth_headers, peca_data):
        create_resp = client.post(
            "/api/v1/pecas/", json=peca_data, headers=auth_headers
        )
        peca_id = create_resp.json()["id"]
        response = client.patch(
            f"/api/v1/pecas/{peca_id}/desativar", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["ativo"] is False

    def test_ativar_peca(self, client, auth_headers, peca_data):
        create_resp = client.post(
            "/api/v1/pecas/", json=peca_data, headers=auth_headers
        )
        peca_id = create_resp.json()["id"]
        client.patch(f"/api/v1/pecas/{peca_id}/desativar", headers=auth_headers)
        response = client.patch(f"/api/v1/pecas/{peca_id}/ativar", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["ativo"] is True

    def test_buscar_peca_inexistente(self, client, auth_headers):
        response = client.get("/api/v1/pecas/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_atualizar_peca_inexistente(self, client, auth_headers):
        response = client.put(
            "/api/v1/pecas/9999", json={"preco": 100.0}, headers=auth_headers
        )
        assert response.status_code == 404

    def test_desativar_peca_inexistente(self, client, auth_headers):
        response = client.patch("/api/v1/pecas/9999/desativar", headers=auth_headers)
        assert response.status_code == 404

    def test_ativar_peca_inexistente(self, client, auth_headers):
        response = client.patch("/api/v1/pecas/9999/ativar", headers=auth_headers)
        assert response.status_code == 404

    def test_listar_pecas_com_inativos(self, client, auth_headers, peca_data):
        create_resp = client.post(
            "/api/v1/pecas/", json=peca_data, headers=auth_headers
        )
        peca_id = create_resp.json()["id"]
        client.patch(f"/api/v1/pecas/{peca_id}/desativar", headers=auth_headers)
        response = client.get(
            "/api/v1/pecas/?apenas_ativos=false", headers=auth_headers
        )
        assert response.status_code == 200
        ids = [p["id"] for p in response.json()]
        assert peca_id in ids

    @patch("app.services.peca_service.publicar_notificacao")
    def test_ajustar_quantidade_peca(self, mock_pub, client, auth_headers, peca_data):
        create_resp = client.post(
            "/api/v1/pecas/", json=peca_data, headers=auth_headers
        )
        peca_id = create_resp.json()["id"]
        response = client.patch(
            f"/api/v1/pecas/{peca_id}/quantidade",
            json={"quantidade_entrada": 10},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["quantidade_estoque"] == 60

    @patch("app.services.peca_service.publicar_notificacao")
    def test_ajustar_quantidade_com_alerta_estoque(
        self, mock_pub, client, auth_headers
    ):
        create_resp = client.post(
            "/api/v1/pecas/",
            json={
                "nome": "Peça Crítica",
                "preco": 10.0,
                "quantidade_estoque": 5,
                "estoque_minimo": 10,
            },
            headers=auth_headers,
        )
        peca_id = create_resp.json()["id"]
        response = client.patch(
            f"/api/v1/pecas/{peca_id}/quantidade",
            json={"quantidade_entrada": 1},
            headers=auth_headers,
        )
        assert response.status_code == 200
        # estoque=6, estoque_minimo=10 → disponivel=6 ≤ 10 → alert emitted
        calls = [str(c) for c in mock_pub.call_args_list]
        assert any("AlertaDeEstoqueEmitido" in c for c in calls)

    def test_ajustar_quantidade_invalida(self, client, auth_headers, peca_data):
        create_resp = client.post(
            "/api/v1/pecas/", json=peca_data, headers=auth_headers
        )
        peca_id = create_resp.json()["id"]
        response = client.patch(
            f"/api/v1/pecas/{peca_id}/quantidade",
            json={"quantidade_entrada": 0},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @patch("app.services.peca_service.publicar_notificacao")
    def test_criar_peca_eventos_publicados(self, mock_pub, client, auth_headers):
        response = client.post(
            "/api/v1/pecas/",
            json={"nome": "Peça Teste", "preco": 20.0, "quantidade_estoque": 15},
            headers=auth_headers,
        )
        assert response.status_code == 201
        event_names = [c.args[0] for c in mock_pub.call_args_list]
        assert "PecaCadastrada" in event_names
        assert "EstoqueReposto" in event_names

    @patch("app.services.peca_service.publicar_notificacao")
    def test_criar_peca_sem_estoque_inicial(self, mock_pub, client, auth_headers):
        response = client.post(
            "/api/v1/pecas/",
            json={"nome": "Peça Zerada", "preco": 5.0, "quantidade_estoque": 0},
            headers=auth_headers,
        )
        assert response.status_code == 201
        event_names = [c.args[0] for c in mock_pub.call_args_list]
        assert "PecaCadastrada" in event_names
        assert "EstoqueReposto" not in event_names


class TestServicosAPIEdgeCases:
    def test_buscar_servico_inexistente(self, client, auth_headers):
        response = client.get("/api/v1/servicos/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_atualizar_servico_inexistente(self, client, auth_headers):
        response = client.put(
            "/api/v1/servicos/9999", json={"preco": 200.0}, headers=auth_headers
        )
        assert response.status_code == 404

    def test_desativar_servico_inexistente(self, client, auth_headers):
        response = client.patch("/api/v1/servicos/9999/desativar", headers=auth_headers)
        assert response.status_code == 404

    def test_ativar_servico_inexistente(self, client, auth_headers):
        response = client.patch("/api/v1/servicos/9999/ativar", headers=auth_headers)
        assert response.status_code == 404

    def test_listar_servicos_com_inativos(self, client, auth_headers, servico_data):
        create_resp = client.post(
            "/api/v1/servicos/", json=servico_data, headers=auth_headers
        )
        servico_id = create_resp.json()["id"]
        client.patch(f"/api/v1/servicos/{servico_id}/desativar", headers=auth_headers)
        response = client.get(
            "/api/v1/servicos/?apenas_ativos=false", headers=auth_headers
        )
        assert response.status_code == 200
        ids = [s["id"] for s in response.json()]
        assert servico_id in ids
