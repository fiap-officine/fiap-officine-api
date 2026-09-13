from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.schemas.ordem_servico import (
    OrdemServicoCreate,
    OrdemServicoResponse,
    OrdemServicoResumo,
    AlterarStatusRequest,
    AdicionarItemServicoRequest,
    AdicionarItemPecaRequest,
    TempoMedioResponse,
)
from app.domain.enums import StatusOrdemServico
from app.services import ordem_servico_service
from app.api.deps import get_current_user, get_current_cliente, get_optional_cliente
from app.domain.entities.cliente import Cliente

router = APIRouter(prefix="/ordens-servico", tags=["Ordens de Serviço"])


@router.post(
    "/",
    response_model=OrdemServicoResponse,
    status_code=201,
    dependencies=[Depends(get_current_user)],
)
def criar_ordem_servico(dados: OrdemServicoCreate, db: Session = Depends(get_db)):
    """Cria uma nova ordem de serviço com orçamento automático."""
    return ordem_servico_service.criar_ordem_servico(db, dados)


@router.get(
    "/",
    response_model=list[OrdemServicoResumo],
    dependencies=[Depends(get_current_user)],
)
def listar_ordens_servico(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    status: StatusOrdemServico | None = None,
    order_by_status: bool = Query(
        False, description="Ordenar por prioridade de status"
    ),
    exclude_finalizados: bool = Query(
        True, description="Excluir ordens finalizadas/entregues"
    ),
    db: Session = Depends(get_db),
):
    """Lista ordens de serviço com filtro opcional por status."""
    return ordem_servico_service.listar_ordens_servico(
        db,
        skip=skip,
        limit=limit,
        status=status,
        order_by_status=order_by_status,
        exclude_finalizados=exclude_finalizados,
    )


@router.get(
    "/tempo-medio",
    response_model=TempoMedioResponse,
    dependencies=[Depends(get_current_user)],
)
def tempo_medio_execucao(db: Session = Depends(get_db)):
    """Retorna o tempo médio de execução dos serviços finalizados."""
    return ordem_servico_service.obter_tempo_medio(db)


@router.get(
    "/minhas-ordens",
    response_model=list[OrdemServicoResumo],
)
def listar_minhas_ordens(
    current_cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db),
):
    """Lista ordens de serviço do cliente autenticado via token JWT (CPF)."""
    return ordem_servico_service.buscar_ordens_por_cliente(db, current_cliente.id)


@router.get(
    "/acompanhar-cliente/{os_id}",
    response_model=OrdemServicoResponse,
)
def acompanhar_os_cliente(
    os_id: int,
    current_cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db),
):
    """Permite ao cliente autenticado via CPF acompanhar sua ordem de serviço com segurança."""
    from fastapi import HTTPException

    ordem = ordem_servico_service.buscar_ordem_servico(db, os_id)
    if ordem.cliente_id != current_cliente.id:
        raise HTTPException(
            status_code=403, detail="Você não tem permissão para acompanhar esta OS"
        )
    return ordem


# Endpoint para acompanhamento pelo cliente (suporta token JWT ou query param para compatibilidade)
@router.get("/acompanhar/{os_id}", response_model=OrdemServicoResponse)
def acompanhar_ordem_servico(
    os_id: int,
    cpf_cnpj: str | None = Query(None, description="CPF ou CNPJ do cliente"),
    current_cliente: Cliente | None = Depends(get_optional_cliente),
    db: Session = Depends(get_db),
):
    """Permite ao cliente acompanhar o andamento da OS via token JWT (CPF) ou query param."""
    from app.domain.validators import formatar_cpf_cnpj
    from fastapi import HTTPException
    from app.repositories.cliente_repository import ClienteRepository

    ordem = ordem_servico_service.buscar_ordem_servico(db, os_id)
    cliente_repo = ClienteRepository(db)
    cliente = cliente_repo.get_by_id(ordem.cliente_id)

    if current_cliente:
        if not cliente or cliente.id != current_cliente.id:
            raise HTTPException(
                status_code=403, detail="CPF/CNPJ não corresponde ao cliente desta OS"
            )
        return ordem

    if cpf_cnpj:
        cpf_cnpj_limpo = formatar_cpf_cnpj(cpf_cnpj)
        if not cliente or cliente.cpf_cnpj != cpf_cnpj_limpo:
            raise HTTPException(
                status_code=403, detail="CPF/CNPJ não corresponde ao cliente desta OS"
            )
        return ordem

    raise HTTPException(
        status_code=401,
        detail="Autenticação necessária via token Bearer (CPF) ou parâmetro cpf_cnpj",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.get(
    "/{os_id}",
    response_model=OrdemServicoResponse,
    dependencies=[Depends(get_current_user)],
)
def buscar_ordem_servico(os_id: int, db: Session = Depends(get_db)):
    """Busca uma ordem de serviço pelo ID com detalhes completos."""
    return ordem_servico_service.buscar_ordem_servico(db, os_id)


@router.get(
    "/cliente/{cliente_id}",
    response_model=list[OrdemServicoResumo],
    dependencies=[Depends(get_current_user)],
)
def buscar_ordens_por_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Lista ordens de serviço de um cliente específico."""
    return ordem_servico_service.buscar_ordens_por_cliente(db, cliente_id)


@router.patch(
    "/{os_id}/status",
    response_model=OrdemServicoResponse,
    dependencies=[Depends(get_current_user)],
)
def alterar_status(
    os_id: int, dados: AlterarStatusRequest, db: Session = Depends(get_db)
):
    """Altera o status da ordem de serviço seguindo as transições válidas."""
    if dados.novo_status == StatusOrdemServico.EM_DIAGNOSTICO:
        return ordem_servico_service.iniciar_diagnostico(db, os_id, dados.observacao)
    elif dados.novo_status == StatusOrdemServico.AGUARDANDO_APROVACAO:
        return ordem_servico_service.enviar_orcamento(db, os_id, dados.observacao)
    elif dados.novo_status == StatusOrdemServico.EM_EXECUCAO:
        return ordem_servico_service.iniciar_execucao(db, os_id, dados.observacao)
    elif dados.novo_status == StatusOrdemServico.FINALIZADA:
        return ordem_servico_service.finalizar_os(db, os_id, dados.observacao)
    elif dados.novo_status == StatusOrdemServico.ENTREGUE:
        return ordem_servico_service.entregar_veiculo(db, os_id, dados.observacao)

    return ordem_servico_service.alterar_status(
        db, os_id, dados.novo_status, dados.observacao
    )


@router.post(
    "/{os_id}/servicos",
    response_model=OrdemServicoResponse,
    dependencies=[Depends(get_current_user)],
)
def adicionar_servico(
    os_id: int, dados: AdicionarItemServicoRequest, db: Session = Depends(get_db)
):
    """Adiciona um serviço à ordem de serviço (recalcula o orçamento)."""
    return ordem_servico_service.adicionar_servico_os(
        db, os_id, dados.servico_id, dados.quantidade
    )


@router.post(
    "/{os_id}/pecas",
    response_model=OrdemServicoResponse,
    dependencies=[Depends(get_current_user)],
)
def adicionar_peca(
    os_id: int, dados: AdicionarItemPecaRequest, db: Session = Depends(get_db)
):
    """Adiciona uma peça à ordem de serviço (sem baixar estoque imediatamente)."""
    return ordem_servico_service.adicionar_peca_os(
        db, os_id, dados.peca_id, dados.quantidade
    )


@router.delete(
    "/{os_id}/servicos/{item_servico_id}",
    response_model=OrdemServicoResponse,
    dependencies=[Depends(get_current_user)],
)
def remover_servico(os_id: int, item_servico_id: int, db: Session = Depends(get_db)):
    """Remove um serviço da ordem de serviço e recalcula o orçamento."""
    return ordem_servico_service.remover_servico_os(db, os_id, item_servico_id)


@router.delete(
    "/{os_id}/pecas/{item_peca_id}",
    response_model=OrdemServicoResponse,
    dependencies=[Depends(get_current_user)],
)
def remover_peca(os_id: int, item_peca_id: int, db: Session = Depends(get_db)):
    """Remove uma peça da ordem de serviço e devolve ao estoque se a OS já estiver em execução."""
    return ordem_servico_service.remover_peca_os(db, os_id, item_peca_id)


@router.post(
    "/{os_id}/iniciar-diagnostico",
    response_model=OrdemServicoResponse,
    dependencies=[Depends(get_current_user)],
)
def iniciar_diagnostico(
    os_id: int,
    observacao: str | None = Body(None, embed=True),
    db: Session = Depends(get_db),
):
    """Inicia o diagnóstico da ordem de serviço."""
    return ordem_servico_service.iniciar_diagnostico(db, os_id, observacao)


@router.post(
    "/{os_id}/enviar-orcamento",
    response_model=OrdemServicoResponse,
    dependencies=[Depends(get_current_user)],
)
def enviar_orcamento(
    os_id: int,
    observacao: str | None = Body(None, embed=True),
    db: Session = Depends(get_db),
):
    """Envia o orçamento para aprovação do cliente."""
    return ordem_servico_service.enviar_orcamento(db, os_id, observacao)


@router.post(
    "/{os_id}/aprovar-orcamento",
    response_model=OrdemServicoResponse,
    dependencies=[Depends(get_current_user)],
)
def aprovar_orcamento(os_id: int, db: Session = Depends(get_db)):
    """Aprova o orçamento e reserva as peças no estoque."""
    return ordem_servico_service.aprovar_orcamento(db, os_id)


@router.post(
    "/{os_id}/iniciar-execucao",
    response_model=OrdemServicoResponse,
    dependencies=[Depends(get_current_user)],
)
def iniciar_execucao(
    os_id: int,
    observacao: str | None = Body(None, embed=True),
    db: Session = Depends(get_db),
):
    """Inicia a execução dos serviços (requer orçamento aprovado)."""
    return ordem_servico_service.iniciar_execucao(db, os_id, observacao)


@router.post(
    "/{os_id}/finalizar",
    response_model=OrdemServicoResponse,
    dependencies=[Depends(get_current_user)],
)
def finalizar_os(
    os_id: int,
    observacao: str | None = Body(None, embed=True),
    db: Session = Depends(get_db),
):
    """Finaliza a execução da ordem de serviço."""
    return ordem_servico_service.finalizar_os(db, os_id, observacao)


@router.post(
    "/{os_id}/entregar",
    response_model=OrdemServicoResponse,
    dependencies=[Depends(get_current_user)],
)
def entregar_veiculo(
    os_id: int,
    observacao: str | None = Body(None, embed=True),
    db: Session = Depends(get_db),
):
    """Entrega o veículo ao cliente."""
    return ordem_servico_service.entregar_veiculo(db, os_id, observacao)
