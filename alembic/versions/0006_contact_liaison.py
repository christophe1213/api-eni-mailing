"""Contact : table de liaison utilisateur -> utilisateur (sans données dupliquées)

Remplace la table `contact` de la révision 0005 (nom/e-mail/téléphone/note copiés)
par une simple liaison entre deux utilisateurs. Les anciens contacts sont supprimés.

Revision ID: 0006_contact_liaison
Revises: 0005_contact
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_contact_liaison"
down_revision: Union[str, None] = "0005_contact"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_contact_utilisateur_id", table_name="contact")
    op.drop_table("contact")
    op.create_table(
        "contact",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("utilisateur_id", sa.Integer(), nullable=False),
        sa.Column("contact_utilisateur_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["utilisateur_id"], ["utilisateur.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_utilisateur_id"], ["utilisateur.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "utilisateur_id", "contact_utilisateur_id", name="uq_contact_utilisateur_contact"
        ),
        sa.CheckConstraint(
            "utilisateur_id <> contact_utilisateur_id", name="ck_contact_pas_soi_meme"
        ),
    )
    op.create_index("ix_contact_utilisateur_id", "contact", ["utilisateur_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_contact_utilisateur_id", table_name="contact")
    op.drop_table("contact")
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
