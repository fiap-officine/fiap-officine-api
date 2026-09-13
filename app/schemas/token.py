from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None
    cpf: str | None = None
    role: str | None = None
    cliente_id: int | None = None
