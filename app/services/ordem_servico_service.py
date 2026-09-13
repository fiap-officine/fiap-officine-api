from datetime import datetime, timezone
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.domain.entities.ordem_servico import (
    OrdemServico,
    OrdemServicoServico,
    OrdemServicoPeca,
)
from app.domain.enums import StatusOrdemServico, TRANSICOES_VALIDAS
from app.repositories.ordem_servico_repository import OrdemServicoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.veiculo_repository import VeiculoRepository
from app.repositories.servico_repository import ServicoRepository
from app.repositories.peca_repository import PecaRepository
from app.schemas.ordem_servico import OrdemServicoCreate, TempoMedioResponse
from app.infrastructure.redis_client import publicar_notificacao


def criar_ordem_servico(db: Session, dados: OrdemServicoCreate) -> OrdemServico:
    cliente_repo = ClienteRepository(db)
    cliente = cliente_repo.get_by_id(dados.cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    if not cliente.ativo:
        raise HTTPException(
            status_code=400,
            detail="Cliente inativo não pode abrir novas Ordens de Serviço",
        )

    veiculo_repo = VeiculoRepository(db)
    veiculo = veiculo_repo.get_by_id(dados.veiculo_id)
    if not veiculo:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    if veiculo.cliente_id != dados.cliente_id:
        raise HTTPException(
            status_code=400, detail="Veículo não pertence ao cliente informado"
        )

    servico_repo = ServicoRepository(db)
    itens_servico = []
    valor_total = Decimal("0.00")

    if dados.itens_servico:
        for item in dados.itens_servico:
            servico = servico_repo.get_by_id(item.servico_id)
            if not servico:
                raise HTTPException(
                    status_code=404,
                    detail=f"Serviço ID {item.servico_id} não encontrado",
                )
            if not servico.ativo:
                raise HTTPException(
                    status_code=400, detail=f"Serviço '{servico.nome}' está inativo"
                )

            valor_item = servico.preco * item.quantidade
            itens_servico.append(
                OrdemServicoServico(
                    servico_id=item.servico_id,
                    quantidade=item.quantidade,
                    valor_unitario=servico.preco,
                    valor_total=valor_item,
                )
            )
            valor_total += valor_item

    itens_peca = []
    peca_repo = PecaRepository(db)
    if dados.itens_peca:
        for item in dados.itens_peca:
            peca = peca_repo.get_by_id(item.peca_id)
            if not peca:
                raise HTTPException(
                    status_code=404, detail=f"Peça ID {item.peca_id} não encontrada"
                )
            if not peca.ativo:
                raise HTTPException(
                    status_code=400, detail=f"Peça '{peca.nome}' está inativa"
                )

            valor_item = peca.preco * item.quantidade
            itens_peca.append(
                OrdemServicoPeca(
                    peca_id=item.peca_id,
                    quantidade=item.quantidade,
                    valor_unitario=peca.preco,
                    valor_total=valor_item,
                )
            )
            valor_total += valor_item

    ordem = OrdemServico(
        cliente_id=dados.cliente_id,
        veiculo_id=dados.veiculo_id,
        status=StatusOrdemServico.RECEBIDA,
        observacoes=dados.observacoes,
        valor_total=valor_total,
        itens_servico=itens_servico,
        itens_peca=itens_peca,
    )

    os_repo = OrdemServicoRepository(db)
    ordem = os_repo.create(ordem)

    os_repo.adicionar_historico(
        ordem_servico_id=ordem.id,
        status_anterior=None,
        status_novo=StatusOrdemServico.RECEBIDA.value,
        observacao="Ordem de serviço criada",
    )

    try:
        publicar_notificacao(
            "OSAberta",
            {
                "ordem_servico_id": ordem.id,
                "cliente_id": dados.cliente_id,
                "valor_total": str(valor_total),
            },
        )
    except Exception:
        pass

    return ordem


def listar_ordens_servico(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: StatusOrdemServico | None = None,
    order_by_status: bool = False,
    exclude_finalizados: bool = True,
) -> list[OrdemServico]:
    os_repo = OrdemServicoRepository(db)
    return os_repo.get_list(
        status=status,
        order_by_status=order_by_status,
        exclude_finalizados=exclude_finalizados,
        skip=skip,
        limit=limit,
    )


def buscar_ordem_servico(db: Session, os_id: int) -> OrdemServico:
    os_repo = OrdemServicoRepository(db)
    ordem = os_repo.get_by_id(os_id)
    if not ordem:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    return ordem


def buscar_ordens_por_cliente(db: Session, cliente_id: int) -> list[OrdemServico]:
    os_repo = OrdemServicoRepository(db)
    return os_repo.get_by_cliente(cliente_id)


def alterar_status(
    db: Session,
    os_id: int,
    novo_status: StatusOrdemServico,
    observacao: str | None = None,
) -> OrdemServico:
    os_repo = OrdemServicoRepository(db)
    ordem = os_repo.get_by_id(os_id)
    if not ordem:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")

    status_atual = ordem.status
    transicoes_permitidas = TRANSICOES_VALIDAS.get(status_atual, [])
    if novo_status not in transicoes_permitidas:
        raise HTTPException(
            status_code=400,
            detail=f"Transição de '{status_atual.value}' para '{novo_status.value}' não é permitida. "
            f"Transições válidas: {[t.value for t in transicoes_permitidas]}",
        )

    # status_anterior_enum = ordem.status
    status_anterior = ordem.status.value
    ordem.status = novo_status

    # A dedução de estoque foi movida para aprovar_orcamento

    if novo_status == StatusOrdemServico.CANCELADA and ordem.orcamento_aprovado:
        peca_repo = PecaRepository(db)
        for item in ordem.itens_peca:
            peca = peca_repo.get_by_id(item.peca_id)
            if peca:
                peca.quantidade_reservada -= item.quantidade
        try:
            publicar_notificacao("ReservaCancelada", {"ordem_servico_id": os_id})
        except Exception:
            pass

    if novo_status == StatusOrdemServico.FINALIZADA:
        ordem.data_finalizacao = datetime.now(timezone.utc)
        peca_repo = PecaRepository(db)
        for item in ordem.itens_peca:
            peca = peca_repo.get_by_id(item.peca_id)
            if peca:
                peca.quantidade_estoque -= item.quantidade
                peca.quantidade_reservada -= item.quantidade
                disponivel = peca.quantidade_estoque - peca.quantidade_reservada
                if disponivel <= peca.estoque_minimo:
                    try:
                        publicar_notificacao(
                            "AlertaDeEstoqueEmitido",
                            {
                                "peca_id": peca.id,
                                "peca_nome": peca.nome,
                                "disponivel": disponivel,
                                "estoque_minimo": peca.estoque_minimo,
                            },
                        )
                    except Exception:
                        pass
        try:
            publicar_notificacao("EstoqueDebitado", {"ordem_servico_id": os_id})
        except Exception:
            pass
    elif novo_status == StatusOrdemServico.ENTREGUE:
        ordem.data_entrega = datetime.now(timezone.utc)

    os_repo.update(ordem)

    os_repo.adicionar_historico(
        ordem_servico_id=os_id,
        status_anterior=status_anterior,
        status_novo=novo_status.value,
        observacao=observacao,
    )

    event_map = {
        StatusOrdemServico.EM_DIAGNOSTICO: "DiagnosticoIniciado",
        StatusOrdemServico.AGUARDANDO_APROVACAO: "OrcamentoEnviado",
        StatusOrdemServico.EM_EXECUCAO: "ExecucaoIniciada",
        StatusOrdemServico.FINALIZADA: "OSFinalizada",
        StatusOrdemServico.ENTREGUE: "OSEntregue",
        StatusOrdemServico.CANCELADA: "OSCancelada",
    }
    evento = event_map.get(novo_status, "status_alterado")

    try:
        publicar_notificacao(
            evento,
            {
                "ordem_servico_id": os_id,
                "status_anterior": status_anterior,
                "status_novo": novo_status.value,
            },
        )
    except Exception:
        pass

    return ordem


def iniciar_diagnostico(
    db: Session, os_id: int, observacao: str | None = None
) -> OrdemServico:
    return alterar_status(db, os_id, StatusOrdemServico.EM_DIAGNOSTICO, observacao)


def enviar_orcamento(
    db: Session, os_id: int, observacao: str | None = None
) -> OrdemServico:
    return alterar_status(
        db, os_id, StatusOrdemServico.AGUARDANDO_APROVACAO, observacao
    )


def aprovar_orcamento(db: Session, os_id: int) -> OrdemServico:
    os_repo = OrdemServicoRepository(db)
    ordem = os_repo.get_by_id(os_id)
    if not ordem:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")

    if ordem.status != StatusOrdemServico.AGUARDANDO_APROVACAO:
        raise HTTPException(
            status_code=400, detail="Ordem não está aguardando aprovação"
        )

    if ordem.orcamento_aprovado:
        raise HTTPException(status_code=400, detail="Orçamento já foi aprovado")

    peca_repo = PecaRepository(db)
    for item in ordem.itens_peca:
        peca = peca_repo.get_by_id(item.peca_id)
        disponivel = peca.quantidade_estoque - peca.quantidade_reservada
        if disponivel < item.quantidade:
            raise HTTPException(
                status_code=400,
                detail=f"Estoque insuficiente para peça '{peca.nome}' ao aprovar a OS. Disponível: {disponivel}, Necessário: {item.quantidade}",
            )
        peca.quantidade_reservada += item.quantidade

    ordem.orcamento_aprovado = True
    os_repo.update(ordem)

    os_repo.adicionar_historico(
        ordem_servico_id=os_id,
        status_anterior=ordem.status.value,
        status_novo=ordem.status.value,
        observacao="Orçamento Aprovado pelo Cliente",
    )

    try:
        publicar_notificacao("OSAprovada", {"ordem_servico_id": os_id})
        publicar_notificacao("EstoqueReservado", {"ordem_servico_id": os_id})
    except Exception:
        pass

    return ordem


def iniciar_execucao(
    db: Session, os_id: int, observacao: str | None = None
) -> OrdemServico:
    os_repo = OrdemServicoRepository(db)
    ordem = os_repo.get_by_id(os_id)
    if ordem and not ordem.orcamento_aprovado:
        raise HTTPException(
            status_code=400,
            detail="Não é possível iniciar execução sem orçamento aprovado",
        )
    return alterar_status(db, os_id, StatusOrdemServico.EM_EXECUCAO, observacao)


def finalizar_os(
    db: Session, os_id: int, observacao: str | None = None
) -> OrdemServico:
    return alterar_status(db, os_id, StatusOrdemServico.FINALIZADA, observacao)


def entregar_veiculo(
    db: Session, os_id: int, observacao: str | None = None
) -> OrdemServico:
    return alterar_status(db, os_id, StatusOrdemServico.ENTREGUE, observacao)


def adicionar_servico_os(
    db: Session, os_id: int, servico_id: int, quantidade: int = 1
) -> OrdemServico:
    os_repo = OrdemServicoRepository(db)
    ordem = os_repo.get_by_id(os_id)
    if not ordem:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")

    if ordem.status not in [
        StatusOrdemServico.RECEBIDA,
        StatusOrdemServico.EM_DIAGNOSTICO,
    ]:
        raise HTTPException(
            status_code=400, detail="Não é possível adicionar serviços neste status"
        )

    servico_repo = ServicoRepository(db)
    servico = servico_repo.get_by_id(servico_id)
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    valor_item = servico.preco * quantidade
    item = OrdemServicoServico(
        ordem_servico_id=os_id,
        servico_id=servico_id,
        quantidade=quantidade,
        valor_unitario=servico.preco,
        valor_total=valor_item,
    )
    db.add(item)
    ordem.valor_total += valor_item
    os_repo.update(ordem)

    try:
        publicar_notificacao(
            "ServicoAdicionadoAOS",
            {
                "ordem_servico_id": os_id,
                "servico_id": servico_id,
                "quantidade": quantidade,
            },
        )
        publicar_notificacao(
            "OrcamentoGerado",
            {"ordem_servico_id": os_id, "valor_total": str(ordem.valor_total)},
        )
    except Exception:
        pass

    return ordem


def adicionar_peca_os(
    db: Session, os_id: int, peca_id: int, quantidade: int = 1
) -> OrdemServico:
    os_repo = OrdemServicoRepository(db)
    ordem = os_repo.get_by_id(os_id)
    if not ordem:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")

    if ordem.status not in [
        StatusOrdemServico.RECEBIDA,
        StatusOrdemServico.EM_DIAGNOSTICO,
    ]:
        raise HTTPException(
            status_code=400, detail="Não é possível adicionar peças neste status"
        )

    peca_repo = PecaRepository(db)
    peca = peca_repo.get_by_id(peca_id)
    if not peca:
        raise HTTPException(status_code=404, detail="Peça não encontrada")

    disponivel = peca.quantidade_estoque - peca.quantidade_reservada
    if disponivel < quantidade:
        raise HTTPException(
            status_code=400,
            detail=f"Estoque insuficiente. Disponível: {disponivel}",
        )

    valor_item = peca.preco * quantidade
    item = OrdemServicoPeca(
        ordem_servico_id=os_id,
        peca_id=peca_id,
        quantidade=quantidade,
        valor_unitario=peca.preco,
        valor_total=valor_item,
    )
    db.add(item)

    ordem.valor_total += valor_item
    os_repo.update(ordem)

    try:
        publicar_notificacao(
            "PecaVinculadaAOS",
            {"ordem_servico_id": os_id, "peca_id": peca_id, "quantidade": quantidade},
        )
        publicar_notificacao(
            "OrcamentoGerado",
            {"ordem_servico_id": os_id, "valor_total": str(ordem.valor_total)},
        )
    except Exception:
        pass

    return ordem


def remover_servico_os(db: Session, os_id: int, item_servico_id: int) -> OrdemServico:
    os_repo = OrdemServicoRepository(db)
    ordem = os_repo.get_by_id(os_id)
    if not ordem:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")

    if ordem.status in [
        StatusOrdemServico.FINALIZADA,
        StatusOrdemServico.ENTREGUE,
        StatusOrdemServico.CANCELADA,
    ]:
        raise HTTPException(
            status_code=400, detail="Não é possível remover serviços neste status final"
        )

    item_remover = next(
        (item for item in ordem.itens_servico if item.id == item_servico_id), None
    )
    if not item_remover:
        raise HTTPException(
            status_code=404, detail="Item de serviço não encontrado na ordem"
        )

    ordem.valor_total -= item_remover.valor_total
    db.delete(item_remover)
    os_repo.update(ordem)
    return ordem


def remover_peca_os(db: Session, os_id: int, item_peca_id: int) -> OrdemServico:
    os_repo = OrdemServicoRepository(db)
    ordem = os_repo.get_by_id(os_id)
    if not ordem:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")

    if ordem.status in [
        StatusOrdemServico.FINALIZADA,
        StatusOrdemServico.ENTREGUE,
        StatusOrdemServico.CANCELADA,
    ]:
        raise HTTPException(
            status_code=400, detail="Não é possível remover peças neste status final"
        )

    item_remover = next(
        (item for item in ordem.itens_peca if item.id == item_peca_id), None
    )
    if not item_remover:
        raise HTTPException(
            status_code=404, detail="Item de peça não encontrado na ordem"
        )

    if ordem.orcamento_aprovado:
        peca_repo = PecaRepository(db)
        peca = peca_repo.get_by_id(item_remover.peca_id)
        if peca:
            peca.quantidade_reservada -= item_remover.quantidade

    ordem.valor_total -= item_remover.valor_total
    db.delete(item_remover)
    os_repo.update(ordem)

    try:
        publicar_notificacao(
            "PecaRemovidaDaOS",
            {"ordem_servico_id": os_id, "peca_id": item_remover.peca_id},
        )
    except Exception:
        pass

    return ordem


def obter_tempo_medio(db: Session) -> TempoMedioResponse:
    os_repo = OrdemServicoRepository(db)
    tempo_medio, total = os_repo.get_tempo_medio_execucao()
    return TempoMedioResponse(
        tempo_medio_minutos=round(tempo_medio, 2), total_ordens_finalizadas=total
    )
