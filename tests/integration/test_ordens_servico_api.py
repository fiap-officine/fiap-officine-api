from unittest.mock import patch


class TestOrdensServicoAPI:
    def _setup_dados(self, client, auth_headers):
        """Cria cliente, veículo, serviço e peça para testes de OS."""

        resp = client.post(
            "/api/v1/clientes/",
            json={
                "nome": "Cliente OS",
                "cpf_cnpj": "529.982.247-25",
                "email": "os@test.com",
            },
            headers=auth_headers,
        )
        cliente_id = resp.json()["id"]

        resp = client.post(
            "/api/v1/veiculos/",
            json={
                "cliente_id": cliente_id,
                "placa": "ABC1234",
                "marca": "Fiat",
                "modelo": "Uno",
                "ano": 2020,
            },
            headers=auth_headers,
        )
        veiculo_id = resp.json()["id"]

        resp = client.post(
            "/api/v1/servicos/",
            json={
                "nome": "Troca de Óleo",
                "preco": 150.00,
                "tempo_estimado_minutos": 30,
            },
            headers=auth_headers,
        )
        servico_id = resp.json()["id"]

        resp = client.post(
            "/api/v1/pecas/",
            json={"nome": "Filtro de Óleo", "preco": 35.50, "quantidade_estoque": 50},
            headers=auth_headers,
        )
        peca_id = resp.json()["id"]

        return cliente_id, veiculo_id, servico_id, peca_id

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_criar_ordem_servico(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, servico_id, peca_id = self._setup_dados(
            client, auth_headers
        )

        response = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "observacoes": "Revisão completa",
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
                "itens_peca": [{"peca_id": peca_id, "quantidade": 2}],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "recebida"
        assert float(data["valor_total"]) == 221.00
        assert len(data["itens_servico"]) == 1
        assert len(data["itens_peca"]) == 1
        assert len(data["historico"]) == 1

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_criar_os_sem_servico(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, _, _ = self._setup_dados(client, auth_headers)

        response = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_criar_os_veiculo_outro_cliente(self, mock_redis, client, auth_headers):
        """Veículo não pertence ao cliente informado."""
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)

        resp = client.post(
            "/api/v1/clientes/",
            json={"nome": "Outro", "cpf_cnpj": "11222333000181"},
            headers=auth_headers,
        )
        outro_cliente_id = resp.json()["id"]

        response = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": outro_cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        assert response.status_code == 400

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_listar_ordens_servico(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        response = client.get("/api/v1/ordens-servico/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_buscar_os_detalhada(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]
        response = client.get(f"/api/v1/ordens-servico/{os_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == os_id
        assert "itens_servico" in data
        assert "historico" in data

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_fluxo_completo_status(self, mock_redis, client, auth_headers):
        """Testa o fluxo completo: Recebida → Em Diagnóstico → Aguardando Aprovação → Em Execução → Finalizada → Entregue."""
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_diagnostico"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "em_diagnostico"

        resp = client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={
                "novo_status": "aguardando_aprovacao",
                "observacao": "Orçamento enviado",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200

        resp = client.post(
            f"/api/v1/ordens-servico/{os_id}/aprovar-orcamento",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        resp = client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={
                "novo_status": "em_execucao",
                "observacao": "Iniciando após aprovação",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200

        resp = client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "finalizada"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data_finalizacao"] is not None

        resp = client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "entregue"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data_entrega"] is not None

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_transicao_invalida(self, mock_redis, client, auth_headers):
        """Tentar pular etapas deve falhar."""
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "finalizada"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_adicionar_servico_na_os(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]

        resp = client.post(
            "/api/v1/servicos/",
            json={"nome": "Alinhamento", "preco": 80.00, "tempo_estimado_minutos": 45},
            headers=auth_headers,
        )
        novo_servico_id = resp.json()["id"]

        resp = client.post(
            f"/api/v1/ordens-servico/{os_id}/servicos",
            json={"servico_id": novo_servico_id, "quantidade": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert float(resp.json()["valor_total"]) == 230.00

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_adicionar_peca_controle_estoque(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, servico_id, peca_id = self._setup_dados(
            client, auth_headers
        )
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]

        # Vincula peça à OS (sem impacto no estoque ainda)
        resp = client.post(
            f"/api/v1/ordens-servico/{os_id}/pecas",
            json={"peca_id": peca_id, "quantidade": 3},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert float(resp.json()["valor_total"]) == 256.50

        # Estoque físico inalterado antes da aprovação
        resp = client.get(f"/api/v1/pecas/{peca_id}", headers=auth_headers)
        assert resp.json()["quantidade_estoque"] == 50
        assert resp.json()["quantidade_reservada"] == 0

        # Aprovação: reserva (não debita ainda)
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_diagnostico"},
            headers=auth_headers,
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "aguardando_aprovacao"},
            headers=auth_headers,
        )
        client.post(
            f"/api/v1/ordens-servico/{os_id}/aprovar-orcamento", headers=auth_headers
        )

        resp = client.get(f"/api/v1/pecas/{peca_id}", headers=auth_headers)
        assert resp.json()["quantidade_estoque"] == 50  # ainda não debitado
        assert resp.json()["quantidade_reservada"] == 3  # reservado

        # Finalização: débito definitivo
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_execucao"},
            headers=auth_headers,
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "finalizada"},
            headers=auth_headers,
        )

        resp = client.get(f"/api/v1/pecas/{peca_id}", headers=auth_headers)
        assert resp.json()["quantidade_estoque"] == 47  # debitado
        assert resp.json()["quantidade_reservada"] == 0  # reserva zerada

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_estoque_insuficiente(self, mock_redis, client, auth_headers):
        """Estoque insuficiente deve ser detectado na aprovação (não na criação)."""
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)

        # Cria peça com estoque 1
        resp = client.post(
            "/api/v1/pecas/",
            json={"nome": "Peça Rara", "preco": 500.00, "quantidade_estoque": 1},
            headers=auth_headers,
        )
        peca_rara_id = resp.json()["id"]

        # Criação da OS com qtd 5 deve ser aceita (validação é na aprovação)
        response = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
                "itens_peca": [{"peca_id": peca_rara_id, "quantidade": 5}],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        os_id = response.json()["id"]

        # Aprovação falha por estoque insuficiente
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_diagnostico"},
            headers=auth_headers,
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "aguardando_aprovacao"},
            headers=auth_headers,
        )
        resp = client.post(
            f"/api/v1/ordens-servico/{os_id}/aprovar-orcamento", headers=auth_headers
        )
        assert resp.status_code == 400
        assert "Estoque insuficiente" in resp.json()["detail"]

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_acompanhar_os_pelo_cliente(self, mock_redis, client, auth_headers):
        """Endpoint público de acompanhamento com CPF."""
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]

        resp = client.get(
            f"/api/v1/ordens-servico/acompanhar/{os_id}?cpf_cnpj=52998224725"
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == os_id

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_acompanhar_os_cpf_errado(self, mock_redis, client, auth_headers):
        """CPF/CNPJ errado deve retornar 403."""
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]

        resp = client.get(
            f"/api/v1/ordens-servico/acompanhar/{os_id}?cpf_cnpj=00000000000"
        )
        assert resp.status_code == 403

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_tempo_medio_execucao(self, mock_redis, client, auth_headers):
        response = client.get(
            "/api/v1/ordens-servico/tempo-medio", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "tempo_medio_minutos" in data
        assert "total_ordens_finalizadas" in data

    # ── Edge cases: criar OS ─────────────────────────────────────────

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_criar_os_cliente_inexistente(self, mock_redis, client, auth_headers):
        response = client.post(
            "/api/v1/ordens-servico/",
            json={"cliente_id": 9999, "veiculo_id": 1},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_criar_os_cliente_inativo(self, mock_redis, client, auth_headers):
        resp = client.post(
            "/api/v1/clientes/",
            json={"nome": "Inativo", "cpf_cnpj": "11444777000161"},
            headers=auth_headers,
        )
        cliente_id = resp.json()["id"]
        resp = client.post(
            "/api/v1/veiculos/",
            json={
                "cliente_id": cliente_id,
                "placa": "INA0001",
                "marca": "Fiat",
                "modelo": "Uno",
                "ano": 2020,
            },
            headers=auth_headers,
        )
        veiculo_id = resp.json()["id"]
        client.delete(f"/api/v1/clientes/{cliente_id}/desativar", headers=auth_headers)

        response = client.post(
            "/api/v1/ordens-servico/",
            json={"cliente_id": cliente_id, "veiculo_id": veiculo_id},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "inativo" in response.json()["detail"].lower()

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_criar_os_veiculo_inexistente(self, mock_redis, client, auth_headers):
        resp = client.post(
            "/api/v1/clientes/",
            json={"nome": "Cliente VX", "cpf_cnpj": "11444777000161"},
            headers=auth_headers,
        )
        cliente_id = resp.json()["id"]
        response = client.post(
            "/api/v1/ordens-servico/",
            json={"cliente_id": cliente_id, "veiculo_id": 9999},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_criar_os_servico_inexistente(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, _, _ = self._setup_dados(client, auth_headers)
        response = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": 9999, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        assert response.status_code == 404

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_criar_os_servico_inativo(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        client.patch(f"/api/v1/servicos/{servico_id}/desativar", headers=auth_headers)
        response = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "inativo" in response.json()["detail"].lower()

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_criar_os_peca_inexistente(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, _, _ = self._setup_dados(client, auth_headers)
        response = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_peca": [{"peca_id": 9999, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        assert response.status_code == 404

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_criar_os_peca_inativa(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, _, peca_id = self._setup_dados(client, auth_headers)
        client.patch(f"/api/v1/pecas/{peca_id}/desativar", headers=auth_headers)
        response = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_peca": [{"peca_id": peca_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "inativa" in response.json()["detail"].lower()

    # ── Edge cases: busca ──────────────────────────────────────────────

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_buscar_os_inexistente(self, mock_redis, client, auth_headers):
        response = client.get("/api/v1/ordens-servico/9999", headers=auth_headers)
        assert response.status_code == 404

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_buscar_ordens_por_cliente(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        response = client.get(
            f"/api/v1/ordens-servico/cliente/{cliente_id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_listar_os_por_status(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        response = client.get(
            "/api/v1/ordens-servico/?status=recebida", headers=auth_headers
        )
        assert response.status_code == 200
        assert all(o["status"] == "recebida" for o in response.json())

    # ── Edge cases: aprovar orçamento ─────────────────────────────────

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_aprovar_orcamento_ja_aprovado(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_diagnostico"},
            headers=auth_headers,
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "aguardando_aprovacao"},
            headers=auth_headers,
        )
        client.post(
            f"/api/v1/ordens-servico/{os_id}/aprovar-orcamento", headers=auth_headers
        )
        response = client.post(
            f"/api/v1/ordens-servico/{os_id}/aprovar-orcamento", headers=auth_headers
        )
        assert response.status_code == 400
        assert "já foi aprovado" in response.json()["detail"]

    # ── Edge cases: iniciar execução ──────────────────────────────────

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_iniciar_execucao_sem_aprovacao(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_diagnostico"},
            headers=auth_headers,
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "aguardando_aprovacao"},
            headers=auth_headers,
        )
        # tenta iniciar execução sem aprovar orçamento
        response = client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_execucao"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "orçamento aprovado" in response.json()["detail"]

    # ── Edge cases: cancelar com reserva ──────────────────────────────

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_cancelar_os_apos_aprovacao_libera_reserva(
        self, mock_redis, client, auth_headers
    ):
        cliente_id, veiculo_id, servico_id, peca_id = self._setup_dados(
            client, auth_headers
        )
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]
        client.post(
            f"/api/v1/ordens-servico/{os_id}/pecas",
            json={"peca_id": peca_id, "quantidade": 5},
            headers=auth_headers,
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_diagnostico"},
            headers=auth_headers,
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "aguardando_aprovacao"},
            headers=auth_headers,
        )
        client.post(
            f"/api/v1/ordens-servico/{os_id}/aprovar-orcamento", headers=auth_headers
        )

        # status ainda é aguardando_aprovacao → CANCELADA é transição válida
        response = client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "cancelada"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelada"

        # reserva deve ter sido liberada
        resp_peca = client.get(f"/api/v1/pecas/{peca_id}", headers=auth_headers)
        assert resp_peca.json()["quantidade_reservada"] == 0

    # ── Edge cases: adicionar serviço à OS ────────────────────────────

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_adicionar_servico_os_inexistente(self, mock_redis, client, auth_headers):
        _, _, servico_id, _ = self._setup_dados(client, auth_headers)
        response = client.post(
            "/api/v1/ordens-servico/9999/servicos",
            json={"servico_id": servico_id, "quantidade": 1},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_adicionar_servico_status_invalido(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={"cliente_id": cliente_id, "veiculo_id": veiculo_id},
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]
        # avança para aguardando_aprovacao (não permite adicionar serviços)
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_diagnostico"},
            headers=auth_headers,
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "aguardando_aprovacao"},
            headers=auth_headers,
        )
        response = client.post(
            f"/api/v1/ordens-servico/{os_id}/servicos",
            json={"servico_id": servico_id, "quantidade": 1},
            headers=auth_headers,
        )
        assert response.status_code == 400

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_adicionar_servico_inexistente_na_os(
        self, mock_redis, client, auth_headers
    ):
        cliente_id, veiculo_id, _, _ = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={"cliente_id": cliente_id, "veiculo_id": veiculo_id},
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]
        response = client.post(
            f"/api/v1/ordens-servico/{os_id}/servicos",
            json={"servico_id": 9999, "quantidade": 1},
            headers=auth_headers,
        )
        assert response.status_code == 404

    # ── Edge cases: adicionar peça à OS ───────────────────────────────

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_adicionar_peca_os_inexistente(self, mock_redis, client, auth_headers):
        _, _, _, peca_id = self._setup_dados(client, auth_headers)
        response = client.post(
            "/api/v1/ordens-servico/9999/pecas",
            json={"peca_id": peca_id, "quantidade": 1},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_adicionar_peca_status_invalido(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, _, peca_id = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={"cliente_id": cliente_id, "veiculo_id": veiculo_id},
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_diagnostico"},
            headers=auth_headers,
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "aguardando_aprovacao"},
            headers=auth_headers,
        )
        response = client.post(
            f"/api/v1/ordens-servico/{os_id}/pecas",
            json={"peca_id": peca_id, "quantidade": 1},
            headers=auth_headers,
        )
        assert response.status_code == 400

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_adicionar_peca_inexistente_na_os(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, _, _ = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={"cliente_id": cliente_id, "veiculo_id": veiculo_id},
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]
        response = client.post(
            f"/api/v1/ordens-servico/{os_id}/pecas",
            json={"peca_id": 9999, "quantidade": 1},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_adicionar_peca_sem_estoque_disponivel(
        self, mock_redis, client, auth_headers
    ):
        cliente_id, veiculo_id, _, _ = self._setup_dados(client, auth_headers)
        resp = client.post(
            "/api/v1/pecas/",
            json={"nome": "Peça Esgotada", "preco": 10.0, "quantidade_estoque": 2},
            headers=auth_headers,
        )
        peca_esgotada_id = resp.json()["id"]
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={"cliente_id": cliente_id, "veiculo_id": veiculo_id},
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]
        response = client.post(
            f"/api/v1/ordens-servico/{os_id}/pecas",
            json={"peca_id": peca_esgotada_id, "quantidade": 5},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "nsuficiente" in response.json()["detail"]

    # ── Edge cases: remover itens da OS ───────────────────────────────

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_remover_servico_da_os(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        os_data = create_resp.json()
        os_id = os_data["id"]
        item_servico_id = os_data["itens_servico"][0]["id"]

        response = client.delete(
            f"/api/v1/ordens-servico/{os_id}/servicos/{item_servico_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()["itens_servico"]) == 0

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_remover_peca_da_os(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, servico_id, peca_id = self._setup_dados(
            client, auth_headers
        )
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={"cliente_id": cliente_id, "veiculo_id": veiculo_id},
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]
        add_resp = client.post(
            f"/api/v1/ordens-servico/{os_id}/pecas",
            json={"peca_id": peca_id, "quantidade": 2},
            headers=auth_headers,
        )
        item_peca_id = add_resp.json()["itens_peca"][0]["id"]

        response = client.delete(
            f"/api/v1/ordens-servico/{os_id}/pecas/{item_peca_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()["itens_peca"]) == 0

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_remover_peca_apos_aprovacao_libera_reserva(
        self, mock_redis, client, auth_headers
    ):
        cliente_id, veiculo_id, _, peca_id = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={"cliente_id": cliente_id, "veiculo_id": veiculo_id},
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]
        add_resp = client.post(
            f"/api/v1/ordens-servico/{os_id}/pecas",
            json={"peca_id": peca_id, "quantidade": 3},
            headers=auth_headers,
        )
        item_peca_id = add_resp.json()["itens_peca"][0]["id"]

        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_diagnostico"},
            headers=auth_headers,
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "aguardando_aprovacao"},
            headers=auth_headers,
        )
        client.post(
            f"/api/v1/ordens-servico/{os_id}/aprovar-orcamento", headers=auth_headers
        )

        # peça está reservada
        resp_peca = client.get(f"/api/v1/pecas/{peca_id}", headers=auth_headers)
        assert resp_peca.json()["quantidade_reservada"] == 3

        # remove peça → reserva deve ser liberada
        client.delete(
            f"/api/v1/ordens-servico/{os_id}/pecas/{item_peca_id}", headers=auth_headers
        )
        resp_peca = client.get(f"/api/v1/pecas/{peca_id}", headers=auth_headers)
        assert resp_peca.json()["quantidade_reservada"] == 0

    # ── Alerta de estoque na finalização ──────────────────────────────

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_alerta_estoque_emitido_na_finalizacao(
        self, mock_redis, client, auth_headers
    ):
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        # cria peça com estoque_minimo alto para disparar alerta após uso
        resp = client.post(
            "/api/v1/pecas/",
            json={
                "nome": "Peça Crítica",
                "preco": 10.0,
                "quantidade_estoque": 50,
                "estoque_minimo": 45,
            },
            headers=auth_headers,
        )
        peca_critica_id = resp.json()["id"]
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={"cliente_id": cliente_id, "veiculo_id": veiculo_id},
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]
        client.post(
            f"/api/v1/ordens-servico/{os_id}/pecas",
            json={"peca_id": peca_critica_id, "quantidade": 10},
            headers=auth_headers,
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_diagnostico"},
            headers=auth_headers,
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "aguardando_aprovacao"},
            headers=auth_headers,
        )
        client.post(
            f"/api/v1/ordens-servico/{os_id}/aprovar-orcamento", headers=auth_headers
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_execucao"},
            headers=auth_headers,
        )
        resp_fin = client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "finalizada"},
            headers=auth_headers,
        )
        assert resp_fin.status_code == 200
        # disponivel = 50-10=40 ≤ 45 → AlertaDeEstoqueEmitido
        calls = [str(c) for c in mock_redis.call_args_list]
        assert any("AlertaDeEstoqueEmitido" in c for c in calls)

    # ── Tempo médio após finalização ──────────────────────────────────

    @patch("app.services.ordem_servico_service.publicar_notificacao")
    def test_tempo_medio_apos_finalizacao(self, mock_redis, client, auth_headers):
        cliente_id, veiculo_id, servico_id, _ = self._setup_dados(client, auth_headers)
        create_resp = client.post(
            "/api/v1/ordens-servico/",
            json={
                "cliente_id": cliente_id,
                "veiculo_id": veiculo_id,
                "itens_servico": [{"servico_id": servico_id, "quantidade": 1}],
            },
            headers=auth_headers,
        )
        os_id = create_resp.json()["id"]
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_diagnostico"},
            headers=auth_headers,
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "aguardando_aprovacao"},
            headers=auth_headers,
        )
        client.post(
            f"/api/v1/ordens-servico/{os_id}/aprovar-orcamento", headers=auth_headers
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "em_execucao"},
            headers=auth_headers,
        )
        client.patch(
            f"/api/v1/ordens-servico/{os_id}/status",
            json={"novo_status": "finalizada"},
            headers=auth_headers,
        )

        response = client.get(
            "/api/v1/ordens-servico/tempo-medio", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_ordens_finalizadas"] >= 1
        assert data["tempo_medio_minutos"] >= 0
