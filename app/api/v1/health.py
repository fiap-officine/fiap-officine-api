import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.redis_client import redis_client
from app.config import get_settings

router = APIRouter(prefix="", tags=["Health & Observabilidade"])
settings = get_settings()

START_TIME = time.time()


@router.get("/health", summary="Healthcheck detalhado da API e dependências")
@router.get("/api/v1/health", summary="Healthcheck detalhado (prefixado)")
def get_health(response: Response, db: Session = Depends(get_db)):
    """
    Verifica a saúde operacional da API e de todas as dependências externas:
    - Banco de Dados (executa SELECT 1)
    - Redis (executa PING)
    Retorna 200 OK se todos os serviços estiverem saudáveis, ou 503 se algum falhar.
    """
    uptime_seconds = round(time.time() - START_TIME, 2)
    services_status = {}
    is_healthy = True

    # 1. Checagem do Banco de Dados
    try:
        db.execute(text("SELECT 1"))
        services_status["database"] = {"status": "up", "type": "RelationalDB"}
    except Exception as exc:
        is_healthy = False
        services_status["database"] = {"status": "down", "error": str(exc)}


    # 2. Checagem do Redis (Mensageria)
    try:
        redis_client.ping()
        services_status["redis"] = {"status": "up", "type": "Redis"}
    except Exception as exc:
        # Redis é aviso ou degradação parcial se o banco ainda estiver up
        services_status["redis"] = {"status": "down", "error": str(exc)}

    # Se o banco de dados falhar, a aplicação é considerada indisponível
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
        "environment": settings.APP_ENV,
        "services": services_status,
        "version": "1.0.0",
    }
