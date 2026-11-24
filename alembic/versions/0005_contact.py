"""Ajout de la table contact (annuaire de contacts personnels)

Revision ID: 0005_contact
Revises: 0004_email_verification
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_contact"
down_revision: Union[str, None] = "0004_email_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contact",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("utilisateur_id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("telephone", sa.String(length=20), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column(
            "date_creation", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["utilisateur_id"], ["utilisateur.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("utilisateur_id", "email", name="uq_contact_utilisateur_email"),
    )
    op.create_index("ix_contact_utilisateur_id", "contact", ["utilisateur_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_contact_utilisateur_id", table_name="contact")
    op.drop_table("contact")
