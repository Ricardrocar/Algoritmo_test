from pydantic import BaseModel

class ProductBase(BaseModel):
    pass
class Product(ProductBase):
    pass
class ProductCreate(ProductBase):
    pass
class ProductUpdate(ProductBase):
    pass
