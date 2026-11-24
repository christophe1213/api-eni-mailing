import sys
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.db.base_class import Base
from app.models.user import Niveau, Parcours, Utilisateur
from app.models.group import ListeDiffusion, MembreListe
from app.models.template import Modele
from app.models.mail import Message, Boite
from app.core.security import get_password_hash


def init_db(db: Session) -> None:
    # 1. Niveaux
    niveaux_data = [
        ("L1", "Licence 1", 1),
        ("L2", "Licence 2", 2),
        ("L3", "Licence 3", 3),
        ("M1", "Master 1", 4),
        ("M2", "Master 2", 5),
    ]
    for code, libelle, ordre in niveaux_data:
        if not db.get(Niveau, code):
            db.add(Niveau(code=code, libelle=libelle, ordre=ordre))
    db.commit()

    # 2. Parcours
    parcours_data = [
        ("GB", "Génie Logiciel et Base de Données"),
        ("SR", "Administration Systèmes et Réseaux"),
        ("IG", "Informatique Générale"),
    ]
    for code, libelle in parcours_data:
        if not db.get(Parcours, code):
            db.add(Parcours(code=code, libelle=libelle))
    db.commit()

    # 3. Utilisateurs de référence (docs/database/seed.sql)
    pwd_admin = get_password_hash("Admin@2026")
    pwd_default = get_password_hash("Eni@2026")

    users_data = [
        (1, "ENI-ADM-001", "Randrianarisoa", "Hery", "admin@eni.mg", pwd_admin, "ADMIN", None, None, "Administrateur plateforme", "034 00 000 01"),
        (2, "ENI-PER-001", "Rasoanaivo", "Lalao", "scolarite@eni.mg", pwd_default, "PERSONNEL", None, None, "Chef du service de scolarité", "034 00 000 02"),
        (3, "ENI-PER-002", "Andriamanana", "Fidy", "direction@eni.mg", pwd_default, "PERSONNEL", None, None, "Directeur des études", "034 00 000 03"),
        (4, "ENI-ENS-001", "Rakotomalala", "Jean", "jean.rakotomalala@eni.mg", pwd_default, "ENSEIGNANT", None, None, "Enseignant – Base de données", None),
        (5, "ENI-ENS-002", "Razafindrabe", "Mialy", "mialy.razafindrabe@eni.mg", pwd_default, "ENSEIGNANT", None, None, "Enseignante – Réseaux", None),
        (6, "ENI-ENS-003", "Ravelojaona", "Tiana", "tiana.ravelojaona@eni.mg", pwd_default, "ENSEIGNANT", None, None, "Enseignant – Génie logiciel", None),
        (7, "ENI-2024-0101", "Rabe", "Toky", "toky.rabe@eni.mg", pwd_default, "ETUDIANT", "L3", "GB", None, None),
        (8, "ENI-2024-0102", "Rakotoarisoa", "Nomena", "nomena.rakotoarisoa@eni.mg", pwd_default, "ETUDIANT", "L3", "GB", None, None),
        (9, "ENI-2024-0103", "Andrianjaka", "Sitraka", "sitraka.andrianjaka@eni.mg", pwd_default, "ETUDIANT", "L3", "SR", None, None),
        (10, "ENI-2025-0201", "Raharison", "Fanja", "fanja.raharison@eni.mg", pwd_default, "ETUDIANT", "L2", "IG", None, None),
        (11, "ENI-2025-0202", "Ramanantsoa", "Hasina", "hasina.ramanantsoa@eni.mg", pwd_default, "ETUDIANT", "L2", "GB", None, None),
        (12, "ENI-2023-0050", "Rajaonarison", "Kanto", "kanto.rajaonarison@eni.mg", pwd_default, "ETUDIANT", "M1", "GB", None, None),
        (13, "ENI-2026-0301", "Randriamampianina", "Aina", "aina.randriamampianina@eni.mg", pwd_default, "ETUDIANT", "L1", "IG", None, None),
        (14, "ENI-2022-0010", "Rasolofo", "Mamy", "mamy.rasolofo@eni.mg", pwd_default, "ETUDIANT", "M2", "SR", None, None),
    ]

    for uid, mat, nom, prenom, email, pwd, role, niv, parc, fonc, tel in users_data:
        existing = db.scalars(select(Utilisateur).where(Utilisateur.email == email)).first()
        if not existing:
            u = Utilisateur(
                id=uid,
                matricule=mat,
                nom=nom,
                prenom=prenom,
                email=email,
                mot_de_passe=pwd,
                role=role,
                niveau_code=niv,
                parcours_code=parc,
                fonction=fonc,
                telephone=tel,
                actif=True,
                is_verified=True,
                en_attente=False,
            )
            db.add(u)
    db.commit()

    # 4. Listes de diffusion
    groups_data = [
        (1, "Tous les étudiants", "etudiants@eni.mg", "Tous les étudiants inscrits", "AUTO", "ETUDIANT", None, None, False, 1),
        (2, "Tous les enseignants", "enseignants@eni.mg", "Corps enseignant", "AUTO", "ENSEIGNANT", None, None, False, 1),
        (3, "L3 – Génie Logiciel", "l3-gb@eni.mg", "Promotion L3 parcours GB", "AUTO", "ETUDIANT", "L3", "GB", True, 2),
        (4, "L3 – tous parcours", "l3@eni.mg", "Promotion L3", "AUTO", "ETUDIANT", "L3", None, True, 2),
        (5, "Club Dev ENI", "club-dev@eni.mg", "Club de développement – projets et hackathons", "MANUELLE", None, None, None, True, 6),
        (6, "Personnel administratif", "personnel@eni.mg", "Services administratifs", "AUTO", "PERSONNEL", None, None, False, 1),
    ]

    for gid, nom, adr, desc, gtype, crole, cniv, cparc, ouv, prop_id in groups_data:
        if not db.get(ListeDiffusion, gid):
            g = ListeDiffusion(
                id=gid,
                nom=nom,
                adresse=adr,
                description=desc,
                type=gtype,
                critere_role=crole,
                critere_niveau=cniv,
                critere_parcours=cparc,
                ouverte_etudiants=ouv,
                proprietaire_id=prop_id,
            )
            db.add(g)
    db.commit()

    # Membres club-dev
    club_members = [6, 7, 8, 11, 12]
    for uid in club_members:
        existing_m = db.scalars(
            select(MembreListe).where(MembreListe.liste_id == 5, MembreListe.utilisateur_id == uid)
        ).first()
        if not existing_m:
            db.add(MembreListe(liste_id=5, utilisateur_id=uid))
    db.commit()

    # 5. Modèles d'annonces
    templates_data = [
        (1, "Convocation examen", "Examens", "Convocation aux examens {{session}} – {{niveau}}",
         "Bonjour,\n\nLes examens de la session {{session}} pour le niveau {{niveau}} débuteront le {{date}}.\nLe planning détaillé est joint à ce message.\n\nLa Scolarité", 2),
        (2, "Réunion pédagogique", "Réunions", "Réunion pédagogique du {{date}}",
         "Chers collègues,\n\nUne réunion pédagogique se tiendra le {{date}} à {{heure}} en {{salle}}.\nOrdre du jour : {{ordre_du_jour}}\n\nLa Direction des études", 3),
        (3, "Absence enseignant", "Informations", "Absence – {{matiere}} du {{date}}",
         "Bonjour à tous,\n\nLe cours de {{matiere}} prévu le {{date}} est annulé. Il sera rattrapé ultérieurement.\n\nCordialement", 2),
    ]

    for tid, titre, cat, obj, corps, aut_id in templates_data:
        if not db.get(Modele, tid):
            db.add(Modele(id=tid, titre=titre, categorie=cat, objet=obj, corps=corps, auteur_id=aut_id))
    db.commit()

    # 6. Messages de bienvenue et de démo
    if db.scalar(select(Message.id).limit(1)) is None:
        now = datetime.now(timezone.utc)
        m1 = Message(
            id=1,
            expediteur_id=2,  # Scolarité
            objet="Bienvenue sur la plateforme ENI Mail",
            corps="Bonjour à toutes et à tous,\n\nBienvenue sur la nouvelle messagerie interne unifiée de l'École Nationale d'Informatique (ENI).\nCette plateforme vous permet de communiquer simplement et de recevoir toutes les communications officielles.\n\nBien cordialement,\nLe Service de la Scolarité",
            priorite="NORMALE",
            est_annonce=True,
            date_envoi=now - timedelta(days=2),
        )
        db.add(m1)
        db.flush()

        # Boîte expéditeur
        db.add(Boite(message_id=m1.id, utilisateur_id=2, type_dest="FROM", dossier="SENT", lu=True))

        # Boîte destinataires (tous les autres utilisateurs)
        for u in db.scalars(select(Utilisateur).where(Utilisateur.id != 2)).all():
            db.add(Boite(message_id=m1.id, utilisateur_id=u.id, type_dest="TO", dossier="INBOX", lu=False))

        db.commit()

    reset_sequences(db)


def reset_sequences(db: Session) -> None:
    """Recale les séquences PostgreSQL après l'insertion d'ID explicites.

    Sans cela, le premier INSERT applicatif (inscription, nouvelle liste…) reprendrait
    l'ID 1 et échouerait sur la clé primaire.
    """
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return
    for table in ("utilisateur", "liste_diffusion", "modele", "message", "boite", "journal", "piece_jointe"):
        db.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
        ))
    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        init_db(db)
        print("Base de donnees initialisee avec succes.")
    finally:
        db.close()

