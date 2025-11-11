from pydantic import BaseModel

class EmailBase(BaseModel):
    pass
class Email(EmailBase):
    pass
class EmailCreate(EmailBase):
    pass
class EmailUpdate(EmailBase):
    pass
