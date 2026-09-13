# 🔧 Oficina Mecânica - Sistema Integrado de Gestão

**Tech Challenge FIAP - Fase 1 (15SOAT)**

Sistema back-end (MVP) para gestão de ordens de serviço, clientes, veículos, peças e serviços de uma oficina mecânica. Desenvolvido com foco em **Domain-Driven Design (DDD)**, boas práticas de **Qualidade de Software** e **Segurança**.

---

## 📋 Funcionalidades

### Gestão de Ordens de Serviço (OS)
- Criação da OS com identificação do cliente por CPF/CNPJ
- Cadastro de veículo (placa, marca, modelo, ano) com validação
- Inclusão de serviços e peças/insumos com controle de estoque
- **Orçamento gerado automaticamente** com base nos serviços e peças
- Notificação via fila Redis ao criar/alterar OS

### Acompanhamento da OS
- Fluxo de status: `Recebida → Em Diagnóstico → Aguardando Aprovação → Em Execução → Finalizada → Entregue`
- Alteração automática com **validação de transições** (não permite pular etapas)
- **Endpoint público** para o cliente acompanhar pelo CPF/CNPJ (sem JWT)
- Histórico completo de alterações de status

### Gestão Administrativa
- CRUD completo de **Clientes**
- CRUD completo de **Veículos**
- CRUD completo de **Serviços**
- CRUD completo de **Peças e Insumos** (com controle de estoque)
- **Monitoramento do tempo médio** de execução dos serviços

### Segurança
- Autenticação **JWT** para todas as APIs administrativas
- Validação de **CPF/CNPJ** com algoritmo oficial dos dígitos verificadores
- Validação de **placa** nos formatos brasileiro antigo (ABC-1234) e Mercosul (ABC1D23)
- Hash de senhas com **bcrypt**
- Execução em container como **usuário não-root**
- CORS configurado

---

## 🏗️ Arquitetura

Monolito com **arquitetura em camadas** seguindo princípios de DDD:

```
app/
├── domain/              # Camada de Domínio
│   ├── entities/        # Entidades (SQLAlchemy models)
│   ├── enums.py         # Enums e transições de status
│   └── validators.py    # Validadores de CPF, CNPJ e Placa
├── schemas/             # Schemas Pydantic (request/response)
├── repositories/        # Camada de Repositório (acesso a dados)
├── services/            # Camada de Serviço (lógica de negócio)
├── api/                 # Camada de API (rotas FastAPI)
│   ├── deps.py          # Dependencies (auth, DB session)
│   └── v1/              # Endpoints versão 1
├── infrastructure/      # Infraestrutura (DB, Redis)
├── main.py              # Entry point FastAPI
├── config.py            # Configurações via env vars
└── worker.py            # Worker Redis para notificações
```

### Justificativa do Banco de Dados

**PostgreSQL** foi escolhido por:
- **ACID compliance**: Garante integridade transacional, essencial para controle de estoque e ordens de serviço
- **Suporte a tipos avançados**: ENUM nativo para status, NUMERIC para valores monetários
- **Relações complexas**: Excelente para JOINs entre clientes, veículos, OS e itens
- **Maturidade e confiabilidade**: Banco robusto, amplamente utilizado em produção
- **Ecossistema Python**: Integração nativa com SQLAlchemy e Alembic

### Tecnologias
| Tecnologia | Uso |
|---|---|
| **Python 3.12** | Linguagem principal |
| **FastAPI** | Framework web (alta performance, tipagem, Swagger automático) |
| **SQLAlchemy 2.0** | ORM para acesso ao banco |
| **PostgreSQL 16** | Banco de dados relacional |
| **Redis 7** | Fila de notificações (mensageria) |
| **Alembic** | Migrations de banco de dados |
| **Docker / Docker Compose** | Containerização e orquestração |
| **Pytest** | Testes unitários e de integração |
| **JWT (python-jose)** | Autenticação |
| **bcrypt** | Hash de senhas |

---

## 🚀 Como Executar

### Pré-requisitos
- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/install/) instalados

### Subir o ambiente completo

```bash
# Clonar o repositório
git clone <url-do-repositorio>
cd FiapTech

# Copiar variáveis de ambiente
cp .env.example .env

# Subir todos os serviços (API + DB + Redis + Worker)
docker compose up --build
```

A API estará disponível em: **http://localhost:8000**

### Documentação Swagger
- **Swagger UI** (com o sistema rodando): http://localhost:8000/docs
- **ReDoc** (com o sistema rodando): http://localhost:8000/redoc
- **Collection completa da API (OpenAPI/Swagger)**: [docs/openapi.json](docs/openapi.json) — importável diretamente no Postman, Insomnia ou no [Swagger Editor](https://editor.swagger.io/), sem precisar rodar o sistema

---

## 🧪 Testes

### Executar testes localmente

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar todos os testes com cobertura
pytest

# Executar apenas testes unitários
pytest tests/unit/

# Executar apenas testes de integração
pytest tests/integration/

# Ver relatório de cobertura HTML (gerado em htmlcov/)
pytest --cov-report=html
```

### Executar testes no Docker

```bash
docker compose run --rm api pytest
```

---

## 📡 Endpoints da API

### Autenticação
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/v1/auth/register` | Registrar usuário admin |
| POST | `/api/v1/auth/login` | Login (retorna JWT) |
| GET | `/api/v1/auth/me` | Perfil do usuário autenticado |

### Clientes (requer JWT)
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/v1/clientes/` | Criar cliente |
| GET | `/api/v1/clientes/` | Listar clientes |
| GET | `/api/v1/clientes/{id}` | Buscar cliente por ID |
| GET | `/api/v1/clientes/cpf-cnpj/{doc}` | Buscar por CPF/CNPJ |
| PUT | `/api/v1/clientes/{id}` | Atualizar cliente |
| DELETE | `/api/v1/clientes/{id}` | Remover cliente |

### Veículos (requer JWT)
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/v1/veiculos/` | Cadastrar veículo |
| GET | `/api/v1/veiculos/` | Listar veículos |
| GET | `/api/v1/veiculos/{id}` | Buscar veículo |
| GET | `/api/v1/veiculos/cliente/{id}` | Veículos do cliente |
| PUT | `/api/v1/veiculos/{id}` | Atualizar veículo |
| DELETE | `/api/v1/veiculos/{id}` | Remover veículo |

### Serviços (requer JWT)
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/v1/servicos/` | Criar serviço |
| GET | `/api/v1/servicos/` | Listar serviços |
| GET | `/api/v1/servicos/{id}` | Buscar serviço |
| PUT | `/api/v1/servicos/{id}` | Atualizar serviço |
| DELETE | `/api/v1/servicos/{id}` | Remover serviço |

### Peças e Insumos (requer JWT)
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/v1/pecas/` | Criar peça |
| GET | `/api/v1/pecas/` | Listar peças |
| GET | `/api/v1/pecas/{id}` | Buscar peça |
| PUT | `/api/v1/pecas/{id}` | Atualizar peça/estoque |
| DELETE | `/api/v1/pecas/{id}` | Remover peça |

### Ordens de Serviço
| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| POST | `/api/v1/ordens-servico/` | JWT | Criar OS (orçamento automático) |
| GET | `/api/v1/ordens-servico/` | JWT | Listar OS (filtro por status) |
| GET | `/api/v1/ordens-servico/{id}` | JWT | Detalhes da OS |
| GET | `/api/v1/ordens-servico/cliente/{id}` | JWT | OS do cliente |
| GET | `/api/v1/ordens-servico/acompanhar/{id}?cpf_cnpj=` | **Público** | Acompanhamento pelo cliente |
| PATCH | `/api/v1/ordens-servico/{id}/status` | JWT | Alterar status |
| POST | `/api/v1/ordens-servico/{id}/servicos` | JWT | Adicionar serviço à OS |
| POST | `/api/v1/ordens-servico/{id}/pecas` | JWT | Adicionar peça à OS |
| GET | `/api/v1/ordens-servico/tempo-medio` | JWT | Tempo médio de execução |

---

## 🔒 Segurança

- **JWT** com expiração configurável para APIs administrativas
- **Validação de CPF/CNPJ** com algoritmo de dígitos verificadores
- **Validação de Placa** nos formatos brasileiro e Mercosul
- **Hash bcrypt** para armazenamento seguro de senhas
- **Container non-root**: Aplicação roda como usuário sem privilégios
- **Variáveis de ambiente** para dados sensíveis (sem hardcoded secrets)
- **Proteção contra SQL Injection** via ORM SQLAlchemy (queries parametrizadas)
- **Validação de entrada** com Pydantic em todos os endpoints
- **CORS** configurado (restritivo em produção)
- **Transições de status validadas** (impede estados inválidos)

---

## 👥 Grupo 123

| Nome | Email |
|---|---|
| Alexsandro Alves de Medeiros Junior | aleexmedeiros.jr@gmail.com |
| Pedro Henrique Aquino de Brito | phpraquinobrito@gmail.com |

---

## 📄 Links

- **Repositório**: https://github.com/SrMedeirosJr/Pos-Tech-Fiap
- **Collection completa da API (OpenAPI/Swagger)**: [docs/openapi.json](docs/openapi.json)
- **Vídeo demonstrativo**: [https://youtu.be/zXHErk-LFGA]

---

## 📦 Fase 2 — Entregáveis e evolução

A aplicação já incorpora os principais requisitos da segunda fase para o desafio:

- APIs de abertura e consulta de OS.
- Webhook de aprovação de orçamento com autenticação opcional via token compartilhado.
- Webhook de atualização de status via automação/e-mail.
- Listagem de ordens com priorização de status e exclusão lógica de OS finalizadas/entregues.
- Estrutura de CI/CD, Kubernetes e Terraform para deploy local/cluster.

### Variáveis de ambiente importantes

Adicione ao seu `.env`:

```bash
WEBHOOK_SHARED_SECRET=change-me
```

Os webhooks aceitam o header `x-webhook-token` com o mesmo valor configurado.

### Deploy via CI/CD

O workflow de deploy em [.github/workflows/deploys.yml](.github/workflows/deploys.yml) executa:

- instalação de dependências;
- execução de testes;
- build da imagem Docker;
- validação do Terraform;
- validação dos manifests Kubernetes;
- deploy no cluster, quando `KUBE_CONFIG_DATA` estiver configurado.

### Execução local com Kubernetes

Consulte [kubernets.md](kubernets.md) e [Terraform.md](Terraform.md) para instruções completas de deploy local.

---

## 🔁 Fase 2 - Evolução implementada

Esta seção descreve as mudanças realizadas para atender aos requisitos da evolução da aplicação.

- **Endpoint público de Webhooks de Aprovação de Orçamento**: `/api/v1/webhooks/aprovacao-orcamento` — aceita notificações externas de aprovação/recusa e opcionalmente inicia execução.
- **Webhook para atualização via e-mail**: `/api/v1/webhooks/email-status` — permite que ferramentas externas atualizem o status da OS (útil para integrações por e-mail ou automação).
- **Listagem de Ordens com ordenação por prioridade de status**: adicionada opção `order_by_status=true` para ordenar por prioridade (Em Execução > Aguardando Aprovação > Diagnóstico > Recebida) e `exclude_finalizados=true` para excluir ordens finalizadas/entregues da listagem.
- **Exclusão lógica de ordens finalizadas/entregues na listagem**: por padrão ordens em `finalizada` e `entregue` são filtradas da listagem quando `exclude_finalizados` está ativo.
- **Refatoração pontual para clareza e separação de responsabilidades**: reorganizadas consultas de repositório para suportar filtros/ordenações, e propagação dos parâmetros pelas camadas de service e rota.
- **Testes básicos**: adicionados testes de integração leve cobrindo os webhooks (mocks) para garantir contratos de API.

---

## 🛡️ Autenticação Serverless & Proteção de Rotas Sensíveis por CPF

A aplicação integra-se com a Function Serverless (`fiap-officine-lambda`) e com o **AWS API Gateway HTTP API v2**:

### 1. Rotas de Autenticação via CPF
* `POST /api/v1/auth/cliente`: Autentica o cliente titular validando o CPF (módulo 11) e emitindo token JWT assinado. Suporta delegação automática para a Lambda via `AUTH_LAMBDA_URL` com fallback local resiliente.
* `GET /api/v1/auth/cliente/status/{cpf}`: Consulta se o CPF existe na base e se o cadastro está ativo.
* `GET /api/v1/auth/cliente/me`: Retorna os dados do cliente titular autenticado via token JWT.

### 2. Rotas Sensíveis Protegidas por CPF
* `GET /api/v1/ordens-servico/minhas-ordens`: Retorna exclusivamente as ordens de serviço pertencentes ao cliente autenticado via JWT (`Bearer`).
* `GET /api/v1/ordens-servico/acompanhar-cliente/{os_id}`: Permite ao cliente titular acompanhar o status da sua ordem, com validação de titularidade (retorna 403 caso a O.S. pertença a outro cliente).
* `GET /api/v1/veiculos/meus-veiculos`: Lista apenas os veículos registrados sob o CPF do cliente autenticado.
* `GET /api/v1/clientes/me`: Dados cadastrais do cliente titular logado.

---

## 🔒 Governança de Branches e CI/CD

Em conformidade com os requisitos do Tech Challenge:
* **Branches Protegidas**: `main` (Produção) e `develop` (Homologação) possuem proteção ativa contra commits diretos.
* **Uso Obrigatório de Pull Requests**: Todo código deve ser submetido via PR com aprovação e passagem obrigatória das pipelines em [.github/workflows/pull_requests.yml](.github/workflows/pull_requests.yml).
* **Deploy Automático por Ambiente**:
  - Push/Merge em `develop` ➔ Deploy automático para o cluster Kubernetes de **Homologação**.
  - Push/Merge em `main` ➔ Deploy automático para o cluster Kubernetes de **Produção**.

---

## 📊 Monitoramento e Observabilidade (New Relic)

A aplicação conta com observabilidade nativa e integração completa com o **New Relic**:

### 1. Rotas Abertas no API Gateway para Visualização & Monitoramento
As seguintes rotas públicas não exigem autorização e podem ser acessadas diretamente via navegador ou API Gateway:
* `GET https://kai652jumh.execute-api.sa-east-1.amazonaws.com/health`: Healthcheck aprofundado (PostgreSQL `SELECT 1` + Redis `PING`).
* `GET https://kai652jumh.execute-api.sa-east-1.amazonaws.com/api/v1/health`: Endpoint de saúde prefixado.
* `GET https://kai652jumh.execute-api.sa-east-1.amazonaws.com/docs`: Documentação Swagger interativa aberta.
* `GET https://kai652jumh.execute-api.sa-east-1.amazonaws.com/openapi.json`: Especificação OpenAPI completa.
* `GET https://kai652jumh.execute-api.sa-east-1.amazonaws.com/redoc`: Documentação técnica ReDoc.

### 2. Logs Estruturados em JSON & Correlação
* Todos os logs são emitidos no formato JSON contendo `timestamp`, `level`, `service`, `correlation_id`, `request_id`, `duration_ms`, `trace_id` e `span_id`.
* O middleware captura ou gera o header `X-Correlation-ID`, propagando o identificador ao longo de todo o ciclo assíncrono.

### 3. Métricas de Cluster Kubernetes
* O manifesto [`k8s/newrelic-infrastructure.yaml`](k8s/newrelic-infrastructure.yaml) roda como um DaemonSet no cluster K3s coletando métricas de CPU, memória, restarts de pods e nós.

### 4. Dashboards NRQL e Alertas
* Documentação completa de consultas NRQL para volume diário de OS, tempo médio de execução por status, latência (p50, p95, p99) e alertas de falhas de transição disponível em [docs/observability.md](file:///c:/Users/phpra/projects/fiap-pos/docs/observability.md).



