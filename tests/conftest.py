import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.infrastructure.database import Base, get_db
from app.main import app


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Cria tabelas e fornece uma sessão de teste limpa por teste."""

    from app.domain.entities.usuario import Usuario  # noqa
    from app.domain.entities.cliente import Cliente  # noqa
    from app.domain.entities.veiculo import Veiculo  # noqa
    from app.domain.entities.servico import Servico  # noqa
    from app.domain.entities.peca import Peca  # noqa
    from app.domain.entities.ordem_servico import (  # noqa
        OrdemServico,
        OrdemServicoServico,
        OrdemServicoPeca,
        OrdemServicoHistorico,
    )

    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """TestClient do FastAPI com override do DB."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """Registra um usuário e retorna headers com token JWT."""

    client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin_test",
            "email": "admin@test.com",
            "nome_completo": "Admin Teste",
            "password": "senha12345",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin_test", "password": "senha12345"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def cliente_data():
    """Dados válidos para criação de cliente."""
    return {
        "nome": "João da Silva",
        "cpf_cnpj": "529.982.247-25",
        "email": "joao@email.com",
        "telefone": "11999999999",
        "endereco": "Rua Teste, 123",
    }


@pytest.fixture
def veiculo_data():
    """Dados válidos para criação de veículo."""
    return {
        "placa": "ABC1234",
        "marca": "Fiat",
        "modelo": "Uno",
        "ano": 2020,
    }


@pytest.fixture
def servico_data():
    """Dados válidos para criação de serviço."""
    return {
        "nome": "Troca de Óleo",
        "descricao": "Troca completa de óleo do motor",
        "preco": 150.00,
        "tempo_estimado_minutos": 30,
    }


@pytest.fixture
def peca_data():
    """Dados válidos para criação de peça."""
    return {
        "nome": "Filtro de Óleo",
        "descricao": "Filtro de óleo motor",
        "preco": 35.50,
        "quantidade_estoque": 50,
    }
