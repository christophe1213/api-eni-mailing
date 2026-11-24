"""Ajout de la table otp_code et utilisateur.is_verified

Revision ID: 0003_otp_verification
Revises: 0002_en_attente
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_otp_verification"
down_revision: Union[str, None] = "0002_en_attente"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Ajout de is_verified sur utilisateur (par défaut True pour les comptes existants)
    op.add_column(
        "utilisateur",
        sa.Column("is_verified", sa.Boolean(), server_default=sa.true(), nullable=False),
    )

    # 2. Création de la table otp_code
    op.create_table(
        "otp_code",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.String(length=50), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_used", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["utilisateur.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_otp_code_user_id",
        "otp_code",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_otp_code_user_purpose_used",
        "otp_code",
        ["user_id", "purpose", "is_used"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_otp_code_user_purpose_used", table_name="otp_code")
    op.drop_index("ix_otp_code_user_id", table_name="otp_code")
    op.drop_table("otp_code")
    op.drop_column("utilisateur", "is_verified")

