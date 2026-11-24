# app/db/base.py
# Cet import rassemble tous les modèles pour qu'Alembic puisse les détecter automatiquement via Base.metadata
from app.db.base_class import Base  # noqa
from app.models.user import Niveau, Parcours, Utilisateur  # noqa
from app.models.group import ListeDiffusion, MembreListe  # noqa
from app.models.mail import Message, MessageListe, Boite, PieceJointe  # noqa
from app.models.template import Modele  # noqa
from app.models.contact import Contact  # noqa
from app.models.audit import Journal  # noqa

