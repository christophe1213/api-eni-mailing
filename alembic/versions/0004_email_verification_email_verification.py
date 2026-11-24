"""email_verification

Revision ID: 0004_email_verification
Revises: 0003_otp_verification
Create Date: 2026-11-14 02:10:18.312883+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_email_verification'
down_revision: Union[str, None] = '0003_otp_verification'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('utilisateur', sa.Column('email_verification', sa.String(length=150), nullable=True))
    op.add_column('utilisateur', sa.Column('email_verification_verifie', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_unique_constraint('uq_utilisateur_email_verification', 'utilisateur', ['email_verification'])
    op.create_check_constraint(
        'ck_email_verification_distinct',
        'utilisateur',
        'email_verification IS NULL OR email_verification <> email',
    )


def downgrade() -> None:
    op.drop_constraint('ck_email_verification_distinct', 'utilisateur', type_='check')
    op.drop_constraint('uq_utilisateur_email_verification', 'utilisateur', type_='unique')
    op.drop_column('utilisateur', 'email_verification_verifie')
    op.drop_column('utilisateur', 'email_verification')