from pydantic import BaseModel, EmailStr
from datetime import date

class ContactSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    birthday: date
    additional_info: str

class ContactResponse(ContactSchema):
    id: int = 1

    class Config:
       from_attributes = True

class UserModel(BaseModel):
    username: str
    password: str