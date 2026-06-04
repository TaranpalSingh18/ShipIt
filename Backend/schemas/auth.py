from pydantic import BaseModel, EmailStr, Field


class Signup(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)
    name: str = Field(max_length=100)

class Login(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)
