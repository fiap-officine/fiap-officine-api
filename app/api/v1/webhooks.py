import os
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.services import ordem_servico_service
from app.domain.enums import StatusOrdemServico

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def verificar_token_webhook(
    x_webhook_token: str | None = Header(default=None, alias="x-webhook-token"),
):
    """Protege os webhooks com um token compartilhado quando configurado."""
    secret = os.getenv("WEBHOOK_SHARED_SECRET", "").strip()
    if not secret:
        return
    if x_webhook_token != secret:
        raise HTTPException(status_code=401, detail="Token de webhook inválido")


@router.post("/aprovacao-orcamento")
def aprovacao_orcamento_webhook(
    payload: dict,
    _token: None = Depends(verificar_token_webhook),
    db: Session = Depends(get_db),
):
    """Recebe notificações externas de aprovação/recusa do orçamento.

    Exemplo de payload:
    {
      "ordem_servico_id": 123,
      "aprovado": true,
      "iniciar_execucao": false
    }
    """
    os_id = payload.get("ordem_servico_id")
    if not os_id:
        raise HTTPException(status_code=400, detail="ordem_servico_id é obrigatório")

    aprovado = bool(payload.get("aprovado", False))
    iniciar_execucao = bool(payload.get("iniciar_execucao", False))

    if aprovado:
        ordem_servico_service.aprovar_orcamento(db, os_id)
        if iniciar_execucao:
            # tenta iniciar execução após aprovação se solicitado
            try:
                ordem_servico_service.iniciar_execucao(db, os_id)
            except Exception:
                # não interrompe o fluxo de aprovação caso não seja possível iniciar execução
                pass
        return {"status": "aprovado", "ordem_servico_id": os_id}
    else:
        # marca como cancelada quando o orçamento é recusado externamente
        ordem_servico_service.alterar_status(
            db, os_id, StatusOrdemServico.CANCELADA, "Orçamento recusado via webhook"
        )
        return {"status": "recusado", "ordem_servico_id": os_id}


@router.post("/email-status")
def email_status_webhook(
    payload: dict,
    _token: None = Depends(verificar_token_webhook),
    db: Session = Depends(get_db),
):
    """Recebe atualizações de status via ferramentas externas (ex: processamento de e-mail).

    Payload esperado:
    {
      "ordem_servico_id": 123,
      "novo_status": "em_execucao",
      "observacao": "Atualizado via e-mail"
    }
    """
    os_id = payload.get("ordem_servico_id")
    novo_status = payload.get("novo_status")
    observacao = payload.get("observacao")

    if not os_id or not novo_status:
        raise HTTPException(
            status_code=400, detail="ordem_servico_id e novo_status são obrigatórios"
        )

    try:
        status_enum = StatusOrdemServico(novo_status)
    except ValueError:
        raise HTTPException(status_code=400, detail="novo_status inválido")

    ordem_servico_service.alterar_status(db, os_id, status_enum, observacao)
    return {"status": "ok", "ordem_servico_id": os_id, "novo_status": novo_status}
