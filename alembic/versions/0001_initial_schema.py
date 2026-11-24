"""initial_schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-11-03 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tables de référence
    op.create_table(
        "niveau",
        sa.Column("code", sa.String(length=5), nullable=False),
        sa.Column("libelle", sa.String(length=50), nullable=False),
        sa.Column("ordre", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )

    op.create_table(
        "parcours",
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("libelle", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )

    # 2. Utilisateur
    op.create_table(
        "utilisateur",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("matricule", sa.String(length=20), nullable=False),
        sa.Column("nom", sa.String(length=80), nullable=False),
        sa.Column("prenom", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("mot_de_passe", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("niveau_code", sa.String(length=5), nullable=True),
        sa.Column("parcours_code", sa.String(length=10), nullable=True),
        sa.Column("fonction", sa.String(length=100), nullable=True),
        sa.Column("telephone", sa.String(length=20), nullable=True),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("notif_email", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("actif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("date_creation", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("derniere_connexion", sa.DateTime(), nullable=True),
        sa.CheckConstraint("role IN ('ADMIN','PERSONNEL','ENSEIGNANT','ETUDIANT')", name="ck_utilisateur_role"),
        sa.CheckConstraint("role <> 'ETUDIANT' OR niveau_code IS NOT NULL", name="ck_etudiant_niveau"),
        sa.ForeignKeyConstraint(["niveau_code"], ["niveau.code"]),
        sa.ForeignKeyConstraint(["parcours_code"], ["parcours.code"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("matricule"),
    )

    # 3. Liste de diffusion & membres
    op.create_table(
        "liste_diffusion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("adresse", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("critere_role", sa.String(length=20), nullable=True),
        sa.Column("critere_niveau", sa.String(length=5), nullable=True),
        sa.Column("critere_parcours", sa.String(length=10), nullable=True),
        sa.Column("ouverte_etudiants", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("proprietaire_id", sa.Integer(), nullable=False),
        sa.Column("date_creation", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("type IN ('AUTO','MANUELLE')", name="ck_liste_type"),
        sa.ForeignKeyConstraint(["critere_niveau"], ["niveau.code"]),
        sa.ForeignKeyConstraint(["critere_parcours"], ["parcours.code"]),
        sa.ForeignKeyConstraint(["proprietaire_id"], ["utilisateur.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("adresse"),
        sa.UniqueConstraint("nom"),
    )

    op.create_table(
        "membre_liste",
        sa.Column("liste_id", sa.Integer(), nullable=False),
        sa.Column("utilisateur_id", sa.Integer(), nullable=False),
        sa.Column("date_ajout", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["liste_id"], ["liste_diffusion.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["utilisateur_id"], ["utilisateur.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("liste_id", "utilisateur_id"),
    )

    # 4. Message & MessageListe
    op.create_table(
        "message",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("expediteur_id", sa.Integer(), nullable=False),
        sa.Column("objet", sa.String(length=255), server_default="", nullable=False),
        sa.Column("corps", sa.Text(), server_default="", nullable=False),
        sa.Column("priorite", sa.String(length=10), server_default="NORMALE", nullable=False),
        sa.Column("est_annonce", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("date_creation", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("date_envoi", sa.DateTime(), nullable=True),
        sa.CheckConstraint("priorite IN ('NORMALE','HAUTE')", name="ck_message_priorite"),
        sa.ForeignKeyConstraint(["expediteur_id"], ["utilisateur.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["message.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "message_liste",
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("liste_id", sa.Integer(), nullable=False),
        sa.Column("type_dest", sa.String(length=5), nullable=False),
        sa.CheckConstraint("type_dest IN ('TO','CC','BCC')", name="ck_msglist_typedest"),
        sa.ForeignKeyConstraint(["liste_id"], ["liste_diffusion.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["message.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("message_id", "liste_id"),
    )

    # 5. Boite (état utilisateur)
    op.create_table(
        "boite",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("utilisateur_id", sa.Integer(), nullable=False),
        sa.Column("type_dest", sa.String(length=5), nullable=False),
        sa.Column("dossier", sa.String(length=15), nullable=False),
        sa.Column("lu", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("favori", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("date_lecture", sa.DateTime(), nullable=True),
        sa.Column("date_suppression", sa.DateTime(), nullable=True),
        sa.CheckConstraint("type_dest IN ('FROM','TO','CC','BCC')", name="ck_boite_typedest"),
        sa.CheckConstraint("dossier IN ('INBOX','SENT','DRAFTS','ARCHIVE','TRASH')", name="ck_boite_dossier"),
        sa.ForeignKeyConstraint(["message_id"], ["message.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["utilisateur_id"], ["utilisateur.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "utilisateur_id", "type_dest", name="uq_boite_dest"),
    )
    op.create_index("idx_boite_user_dossier", "boite", ["utilisateur_id", "dossier", "lu"])

    # 6. Pièces jointes
    op.create_table(
        "piece_jointe",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("nom_fichier", sa.String(length=255), nullable=False),
        sa.Column("type_mime", sa.String(length=100), nullable=False),
        sa.Column("taille", sa.BigInteger(), nullable=False),
        sa.Column("chemin_stockage", sa.String(length=500), nullable=False),
        sa.CheckConstraint("taille <= 10485760", name="ck_piece_taille_max"),
        sa.ForeignKeyConstraint(["message_id"], ["message.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 7. Modèles d'annonces
    op.create_table(
        "modele",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("titre", sa.String(length=120), nullable=False),
        sa.Column("categorie", sa.String(length=50), nullable=False),
        sa.Column("objet", sa.String(length=255), nullable=False),
        sa.Column("corps", sa.Text(), nullable=False),
        sa.Column("auteur_id", sa.Integer(), nullable=False),
        sa.Column("date_maj", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["auteur_id"], ["utilisateur.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 8. Journal d'audit
    op.create_table(
        "journal",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("utilisateur_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("adresse_ip", sa.String(length=45), nullable=True),
        sa.Column("date", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["utilisateur_id"], ["utilisateur.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_journal_date", "journal", [sa.text("date DESC")])


def downgrade() -> None:
    op.drop_index("idx_journal_date", table_name="journal")
    op.drop_table("journal")
    op.drop_table("modele")
    op.drop_table("piece_jointe")
    op.drop_index("idx_boite_user_dossier", table_name="boite")
    op.drop_table("boite")
    op.drop_table("message_liste")
    op.drop_table("message")
    op.drop_table("membre_liste")
    op.drop_table("liste_diffusion")
    op.drop_table("utilisateur")
    op.drop_table("parcours")
    op.drop_table("niveau")

