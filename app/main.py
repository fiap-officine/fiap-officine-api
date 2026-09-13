import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router
from app.api.v1.health import router as health_router
from app.config import get_settings
from app.core.logging import setup_json_logging
from app.core.middleware import ObservabilityMiddleware

settings = get_settings()

# ── Configuração de Logs Estruturados em JSON ──
setup_json_logging(
    service_name=settings.NEW_RELIC_APP_NAME,
    environment=settings.APP_ENV,
    log_level=settings.LOG_LEVEL,
)
logger = logging.getLogger("app.main")

# ── Inicialização do APM New Relic ──────────────
if settings.NEW_RELIC_LICENSE_KEY or os.getenv("NEW_RELIC_LICENSE_KEY"):
    try:
        import newrelic.agent
        # Configurações de ambiente caso não venha de newrelic.ini
        os.environ.setdefault("NEW_RELIC_APP_NAME", settings.NEW_RELIC_APP_NAME)
        os.environ.setdefault("NEW_RELIC_DISTRIBUTED_TRACING_ENABLED", "true")
        os.environ.setdefault("NEW_RELIC_LOG_LEVEL", "info")
        newrelic.agent.initialize()
        logger.info("Agente APM New Relic inicializado com sucesso.")
    except Exception as exc:
        logger.warning(f"Não foi possível inicializar o New Relic: {exc}")

app = FastAPI(
    title="Oficina Mecânica - Sistema de Gestão",
    description=(
        "API RESTful para gestão de ordens de serviço, clientes, veículos, "
        "serviços e peças de uma oficina mecânica. "
        "Desenvolvido para o Tech Challenge FIAP (15SOAT)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middlewares ─────────────────────────────────
app.add_middleware(ObservabilityMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_ENV == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Roteadores ──────────────────────────────────
app.include_router(health_router)
app.include_router(router)


@app.get("/", tags=["Health"])
def root_check():
    """Verifica se a API está no ar."""
    return {"status": "ok", "service": "Oficina Mecânica API", "version": "1.0.0"}

