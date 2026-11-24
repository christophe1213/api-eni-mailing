from typing import Optional
from pydantic import EmailStr
from app.schemas.base import BaseSchema
from app.schemas.user import UserResponse


class LoginPayload(BaseSchema):
    email: EmailStr
    password: str


class Token(BaseSchema):
    token: str
    user: UserResponse


class TokenPayload(BaseSchema):
    sub: Optional[str] = None
    exp: Optional[int] = None


class ChangePasswordPayload(BaseSchema):
    current_password: str
    new_password: str


class ForgotPasswordPayload(BaseSchema):
    email: EmailStr

