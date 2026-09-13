class TestAuthAPI:
    def test_registrar_usuario(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "novo_admin",
                "email": "novo@test.com",
                "nome_completo": "Novo Admin",
                "password": "senha12345",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "novo_admin"
        assert data["email"] == "novo@test.com"
        assert "hashed_password" not in data

    def test_registrar_username_duplicado(self, client):
        payload = {
            "username": "duplicado",
            "email": "dup1@test.com",
            "nome_completo": "Dup",
            "password": "senha12345",
        }
        client.post("/api/v1/auth/register", json=payload)
        payload["email"] = "dup2@test.com"
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 400

    def test_login_sucesso(self, client):

        client.post(
            "/api/v1/auth/register",
            json={
                "username": "login_user",
                "email": "login@test.com",
                "nome_completo": "Login User",
                "password": "senha12345",
            },
        )

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "login_user", "password": "senha12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_credenciais_invalidas(self, client):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "inexistente", "password": "errada"},
        )
        assert response.status_code == 401

    def test_perfil_autenticado(self, client, auth_headers):
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["username"] == "admin_test"

    def test_perfil_sem_token(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
