from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.domain.entities.peca import Peca
from app.repositories.peca_repository import PecaRepository
from app.schemas.peca import PecaCreate, PecaUpdate
from app.infrastructure.redis_client import publicar_notificacao


def criar_peca(db: Session, dados: PecaCreate) -> Peca:
    repo = PecaRepository(db)
    peca = Peca(
        codigo=dados.codigo,
        nome=dados.nome,
        descricao=dados.descricao,
        unidade_medida=dados.unidade_medida,
        preco=dados.preco,
        quantidade_estoque=dados.quantidade_estoque,
        estoque_minimo=dados.estoque_minimo,
        ativo=True,
    )
    peca = repo.create(peca)
    try:
        publicar_notificacao("PecaCadastrada", {"peca_id": peca.id, "nome": peca.nome})
        if dados.quantidade_estoque > 0:
            publicar_notificacao(
                "EstoqueReposto",
                {
                    "peca_id": peca.id,
                    "quantidade_entrada": dados.quantidade_estoque,
                    "estoque_atual": peca.quantidade_estoque,
                },
            )
    except Exception:
        pass
    return peca


def listar_pecas(
    db: Session, skip: int = 0, limit: int = 100, apenas_ativos: bool = True
) -> list[Peca]:
    repo = PecaRepository(db)
    if apenas_ativos:
        return repo.get_ativos(skip=skip, limit=limit)
    return repo.get_all(skip=skip, limit=limit)


def buscar_peca(db: Session, peca_id: int) -> Peca:
    repo = PecaRepository(db)
    peca = repo.get_by_id(peca_id)
    if not peca:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    return peca


def atualizar_peca(db: Session, peca_id: int, dados: PecaUpdate) -> Peca:
    repo = PecaRepository(db)
    peca = repo.get_by_id(peca_id)
    if not peca:
        raise HTTPException(status_code=404, detail="Peça não encontrada")

    update_data = dados.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(peca, field, value)

    return repo.update(peca)


def desativar_peca(db: Session, peca_id: int) -> Peca:
    repo = PecaRepository(db)
    peca = repo.get_by_id(peca_id)
    if not peca:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    peca.ativo = False
    peca = repo.update(peca)
    try:
        publicar_notificacao("PecaDesativada", {"peca_id": peca_id})
    except Exception:
        pass
    return peca


def ativar_peca(db: Session, peca_id: int) -> Peca:
    repo = PecaRepository(db)
    peca = repo.get_by_id(peca_id)
    if not peca:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    peca.ativo = True
    return repo.update(peca)


def ajustar_quantidade_peca(db: Session, peca_id: int, quantidade_entrada: int) -> Peca:
    if quantidade_entrada <= 0:
        raise HTTPException(
            status_code=400, detail="Quantidade de entrada deve ser positiva"
        )
    repo = PecaRepository(db)
    peca = repo.get_by_id(peca_id)
    if not peca:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    peca.quantidade_estoque += quantidade_entrada
    peca = repo.update(peca)
    disponivel = peca.quantidade_estoque - peca.quantidade_reservada
    try:
        publicar_notificacao(
            "EstoqueReposto",
            {
                "peca_id": peca_id,
                "quantidade_entrada": quantidade_entrada,
                "estoque_atual": peca.quantidade_estoque,
            },
        )
        if disponivel <= peca.estoque_minimo:
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
    return peca
