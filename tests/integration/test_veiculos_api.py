class TestVeiculosAPI:
    def _criar_cliente(self, client, auth_headers):
        resp = client.post(
            "/api/v1/clientes/",
            json={
                "nome": "Cliente Veículo",
                "cpf_cnpj": "529.982.247-25",
                "email": "cv@test.com",
            },
            headers=auth_headers,
        )
        return resp.json()["id"]

    def test_criar_veiculo(self, client, auth_headers, veiculo_data):
        cliente_id = self._criar_cliente(client, auth_headers)
        veiculo_data["cliente_id"] = cliente_id
        response = client.post(
            "/api/v1/veiculos/", json=veiculo_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["placa"] == "ABC1234"
        assert data["cliente_id"] == cliente_id

    def test_criar_veiculo_placa_invalida(self, client, auth_headers):
        cliente_id = self._criar_cliente(client, auth_headers)
        response = client.post(
            "/api/v1/veiculos/",
            json={
                "cliente_id": cliente_id,
                "placa": "INVALID",
                "marca": "Fiat",
                "modelo": "Uno",
                "ano": 2020,
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_criar_veiculo_placa_duplicada(self, client, auth_headers, veiculo_data):
        cliente_id = self._criar_cliente(client, auth_headers)
        veiculo_data["cliente_id"] = cliente_id
        client.post("/api/v1/veiculos/", json=veiculo_data, headers=auth_headers)
        response = client.post(
            "/api/v1/veiculos/", json=veiculo_data, headers=auth_headers
        )
        assert response.status_code == 400

    def test_criar_veiculo_cliente_inexistente(
        self, client, auth_headers, veiculo_data
    ):
        veiculo_data["cliente_id"] = 9999
        response = client.post(
            "/api/v1/veiculos/", json=veiculo_data, headers=auth_headers
        )
        assert response.status_code == 404

    def test_listar_veiculos(self, client, auth_headers, veiculo_data):
        cliente_id = self._criar_cliente(client, auth_headers)
        veiculo_data["cliente_id"] = cliente_id
        client.post("/api/v1/veiculos/", json=veiculo_data, headers=auth_headers)
        response = client.get("/api/v1/veiculos/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_buscar_veiculos_por_cliente(self, client, auth_headers, veiculo_data):
        cliente_id = self._criar_cliente(client, auth_headers)
        veiculo_data["cliente_id"] = cliente_id
        client.post("/api/v1/veiculos/", json=veiculo_data, headers=auth_headers)
        response = client.get(
            f"/api/v1/veiculos/cliente/{cliente_id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_atualizar_veiculo(self, client, auth_headers, veiculo_data):
        cliente_id = self._criar_cliente(client, auth_headers)
        veiculo_data["cliente_id"] = cliente_id
        create_resp = client.post(
            "/api/v1/veiculos/", json=veiculo_data, headers=auth_headers
        )
        veiculo_id = create_resp.json()["id"]
        response = client.put(
            f"/api/v1/veiculos/{veiculo_id}",
            json={"marca": "Toyota"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["marca"] == "Toyota"

    def test_deletar_veiculo(self, client, auth_headers, veiculo_data):
        cliente_id = self._criar_cliente(client, auth_headers)
        veiculo_data["cliente_id"] = cliente_id
        create_resp = client.post(
            "/api/v1/veiculos/", json=veiculo_data, headers=auth_headers
        )
        veiculo_id = create_resp.json()["id"]
        response = client.delete(f"/api/v1/veiculos/{veiculo_id}", headers=auth_headers)
        assert response.status_code == 204

    def test_buscar_veiculo_inexistente(self, client, auth_headers):
        response = client.get("/api/v1/veiculos/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_atualizar_veiculo_inexistente(self, client, auth_headers):
        response = client.put(
            "/api/v1/veiculos/9999", json={"marca": "Yamaha"}, headers=auth_headers
        )
        assert response.status_code == 404

    def test_deletar_veiculo_inexistente(self, client, auth_headers):
        response = client.delete("/api/v1/veiculos/9999", headers=auth_headers)
        assert response.status_code == 404
