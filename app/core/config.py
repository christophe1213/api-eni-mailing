import json
import os
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ENI Mail API"
    ENVIRONMENT: str = "development"
    # Préfixe API conforme à la conception et docs/API.md
    API_V1_STR: str = "/api"

    # PostgreSQL
    # localhost en local ; docker-compose.yml fournit sa propre URL (hôte « db »)
    DATABASE_URL: str = "postgresql+psycopg://eni_user:change_this_password@localhost:5432/eni_mailing"

    # JWT Security
    SECRET_KEY: str = "dev_secret_key_change_in_production_super_secure_hash_12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # Stockage des pièces jointes (RG09)
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
    MAX_ATTACHMENT_SIZE: int = 10 * 1024 * 1024  # 10 Mo par fichier
    MAX_MESSAGE_ATTACHMENT_SIZE: int = 25 * 1024 * 1024  # 25 Mo par message
    FORBIDDEN_EXTENSIONS: List[str] = [".exe", ".bat", ".cmd", ".js", ".vbs"]

    # Photo de profil
    AVATAR_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "avatars"
    )
    MAX_AVATAR_SIZE: int = 5 * 1024 * 1024  # 5 Mo
    AVATAR_PIXELS: int = 256  # image finale carrée 256 x 256

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://frontend-eni-mailing.vercel.app",
    ]

    # Configuration SMTP pour envoi d'emails (OTP, notifications)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "no-reply@eni.mg"
    SMTP_FROM_NAME: str = "ENI Mailing"
    SMTP_TLS: bool = True
    # API Brevo (HTTPS) : à privilégier sur Render, qui bloque les ports SMTP sortants
    BREVO_API_KEY: Optional[str] = None
    # Service d'envoi d'e-mails maison (Vercel) : URL de base + clé x-api-key
    MAIL_SERVICE_URL: Optional[str] = None
    MAIL_SERVICE_API_KEY: Optional[str] = None

    # Configuration OTP (One-Time Password)
    OTP_EXPIRE_MINUTES: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_MAX_ATTEMPTS: int = 5

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        # Réécriture uniquement de l'URL brute postgresql:// → dialect psycopg3
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        # On laisse passer postgresql+psycopg:// et postgresql+psycopg2:// inchangés
        return v

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            return json.loads(v)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
