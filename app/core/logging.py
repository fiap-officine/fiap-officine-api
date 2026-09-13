import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ContextVar para propagação do Correlation ID ao longo do ciclo de vida assíncrono
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id_ctx", default=None)


def get_correlation_id() -> Optional[str]:
    """Retorna o correlation ID do contexto atual."""
    return correlation_id_ctx.get()


class JSONLogFormatter(logging.Formatter):
    """
    Formatador de logs estruturados em JSON para envio ao New Relic e stdout.
    Inclui correlação de requisições, métricas e identificadores de tracing distribuído.
    """

    def __init__(self, service_name: str = "fiap-officine-api", environment: str = "production"):
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "service": self.service_name,
            "environment": self.environment,
        }

        # Injeta Correlation ID se presente no contexto
        corr_id = get_correlation_id()
        if corr_id:
            log_entry["correlation_id"] = corr_id

        # Atributos extras passados no log (ex: extra={"path": ..., "status_code": ...})
        for key in ["path", "method", "status_code", "duration_ms", "request_id", "os_id", "cliente_id"]:
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        # Tracing distribuído do New Relic (se o agente estiver carregado)
        try:
            import newrelic.agent
            metadata = newrelic.agent.get_linking_metadata()
            if metadata:
                log_entry["trace_id"] = metadata.get("trace.id")
                log_entry["span_id"] = metadata.get("span.id")
                log_entry["entity_guid"] = metadata.get("entity.guid")
        except Exception:
            pass

        # Exceção rastreada
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_json_logging(service_name: str = "fiap-officine-api", environment: str = "production", log_level: str = "INFO"):
    """Configura o logger raiz para emitir logs estritamente em JSON no stdout."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove handlers anteriores para evitar duplicação
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONLogFormatter(service_name=service_name, environment=environment))
    root_logger.addHandler(handler)

    # Reduz ruído de bibliotecas externas
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return root_logger
