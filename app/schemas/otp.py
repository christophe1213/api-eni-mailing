import re
from typing import Optional
from pydantic import EmailStr, Field, field_validator
from app.schemas.base import BaseSchema


class VerifyOtpPayload(BaseSchema):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, description="Code OTP à 6 chiffres")
    purpose: str = Field(default="REGISTER", description="Objectif du code OTP (ex: REGISTER, PASSWORD_RESET)")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        clean = v.strip()
        if not clean.isdigit() or len(clean) != 6:
            raise ValueError("Le code OTP doit être composé d'exactement 6 chiffres.")
        return clean


class ResendOtpPayload(BaseSchema):
    email: EmailStr
    purpose: str = Field(default="REGISTER", description="Objectif du code OTP")


class VerifyResetOtpPayload(BaseSchema):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, description="Code OTP de réinitialisation")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        clean = v.strip()
        if not clean.isdigit() or len(clean) != 6:
            raise ValueError("Le code OTP doit être composé d'exactement 6 chiffres.")
        return clean


class ResetPasswordPayload(BaseSchema):
    email: EmailStr
    reset_token: str = Field(..., description="Jeton de réinitialisation obtenu après validation OTP")
    new_password: str = Field(..., description="Nouveau mot de passe")

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        # RG12 : 12 caractères minimum, une majuscule, un chiffre et un symbole
        if (
            len(v) < 12
            or not re.search(r"[A-Z]", v)
            or not re.search(r"\d", v)
            or not re.search(r"[^A-Za-z0-9]", v)
        ):
            raise ValueError(
                "Le mot de passe doit comporter au moins 12 caractères, une majuscule, un chiffre et un symbole (RG12)."
            )
        return v


class OtpResponse(BaseSchema):
    success: bool = True
    message: str


class VerifyResetOtpResponse(BaseSchema):
    success: bool = True
    reset_token: str
    message: str

