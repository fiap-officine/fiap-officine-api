"""
Worker de processamento de notificações via Redis.
Consome mensagens da fila e processa (log, email, etc.).
"""

import logging
import signal
from app.infrastructure.redis_client import consumir_notificacao
from app.core.logging import setup_json_logging

setup_json_logging(service_name="fiap-officine-worker", log_level="INFO")
logger = logging.getLogger("worker")

running = True


def handle_signal(signum, frame):
    global running
    logger.info("Recebido sinal de encerramento. Finalizando worker...")
    running = False


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def processar_notificacao(notificacao: dict) -> None:
    """Processa uma notificação recebida da fila."""
    tipo = notificacao.get("tipo")
    dados = notificacao.get("dados", {})

    if tipo in ["os_criada", "OrdemCriada"]:
        logger.info(
            "Nova OS criada - ID: %s, Cliente: %s, Valor: R$ %s",
            dados.get("ordem_servico_id"),
            dados.get("cliente_id"),
            dados.get("valor_total"),
            extra={"os_id": dados.get("ordem_servico_id"), "cliente_id": dados.get("cliente_id")},
        )
    elif tipo in ["status_alterado", "OSFinalizada", "ExecucaoIniciada"]:
        logger.info(
            "Status alterado - OS: %s, De: %s -> Para: %s",
            dados.get("ordem_servico_id"),
            dados.get("status_anterior"),
            dados.get("status_novo"),
            extra={"os_id": dados.get("ordem_servico_id")},
        )
    else:
        logger.warning("Tipo de notificação recebido: %s", tipo)


def main():
    logger.info("Worker de notificações iniciado. Aguardando mensagens...")

    while running:
        try:
            notificacao = consumir_notificacao()
            if notificacao:
                processar_notificacao(notificacao)
        except Exception as e:
            logger.error("Erro ao processar notificação: %s", str(e), exc_info=True)
            try:
                import newrelic.agent
                newrelic.agent.record_custom_event(
                    "WorkerProcessingFailure",
                    {"error": str(e), "service": "fiap-officine-worker"},
                )
            except Exception:
                pass

    logger.info("Worker encerrado.")


if __name__ == "__main__":
    main()
