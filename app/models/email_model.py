from pydantic import BaseModel
from typing import List, Optional


class Producto(BaseModel):
    nombre: str
    cantidad: int
    precio_unitario: float
    total: float


class Totales(BaseModel):
    total: float
    moneda: str


class Adjunto(BaseModel):
    nombre: str
    tipo: str


class EmailDocumento(BaseModel):
    tipo_documento: str
    correo: str
    asunto: str
    fecha: str
    productos: List[Producto]
    totales: Totales
    adjuntos: List[Adjunto]


class EmailBase(BaseModel):
    pass


class Email(EmailBase):
    tipo_documento: Optional[str] = None


class EmailCreate(EmailBase):
    pass


class EmailUpdate(EmailBase):
    pass
