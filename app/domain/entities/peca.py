from typing import Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Integer, String, Numeric, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Base


class Peca(Base):
    __tablename__ = "pecas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    codigo: Mapped[Optional[str]] = mapped_column(
        String(50), unique=True, nullable=True, index=True
    )
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    unidade_medida: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantidade_estoque: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantidade_reservada: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    estoque_minimo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
