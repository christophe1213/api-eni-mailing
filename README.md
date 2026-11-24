# Backend API — ENI Mail

> API REST haute performance pour la plateforme de messagerie et de diffusion interne de l'École Nationale d'Informatique (ENI).
> Conçue avec **FastAPI**, **SQLAlchemy 2.0**, **PostgreSQL** et **Alembic**, interconnectée avec le frontend **Angular 20**.

---

## 1. Architecture du projet

Le backend adopte une architecture propre en couches (*Clean / Layered Architecture*) pour garantir la maintenabilité, l'extensibilité et la conformité stricte au contrat d'API défini dans `docs/API.md` et `docs/CONCEPTION.md` :

```
eni-mailing/                   ← racine du projet
├── docker-compose.yml         # Orchestration Docker (db + api)
├── backend/
│   ├── app/
│   │   ├── core/              # Configuration (pydantic-settings), sécurité (JWT, hachage)
│   │   ├── db/                # Session SQLAlchemy, base déclarative, script d'initialisation (init_db)
│   │   ├── models/            # Modèles de données PostgreSQL (Utilisateur, Message, Boite, Liste, Modele, Journal...)
│   │   ├── schemas/           # Schémas Pydantic avec sérialisation camelCase pour Angular
│   │   ├── repositories/      # Couche d'accès aux données (CRUD, requêtes optimisées, filtres)
│   │   ├── services/          # Logique métier et règles de gestion (RG01 à RG13)
│   │   ├── api/
│   │   │   ├── deps.py        # Injection de dépendances (DB, authentification, vérification des rôles)
│   │   │   └── v1/
│   │   │       ├── endpoints/ # Contrôleurs d'API (auth, users, mails, groups, templates, admin)
│   │   │       └── api.py     # Routeur central
│   │   └── main.py            # Point d'entrée de l'application FastAPI & middlewares CORS
│   ├── alembic/               # Migrations de schéma de base de données
│   ├── tests/                 # Suite de tests automatisés (pytest + TestClient + SQLite en mémoire)
│   ├── requirements.txt       # Dépendances Python
│   ├── Dockerfile             # Image Docker de l'API
│   ├── entrypoint.sh          # migrations → seed → uvicorn
│   └── .env.example           # Variables d'environnement d'exemple
```

---

## 2. Rôles et règles de gestion implémentées

- **Hérarchie des rôles** : `ADMIN ⊃ PERSONNEL ⊃ ENSEIGNANT ⊃ ETUDIANT`
- **RG01 & RG02** : Matricule et email institutionnels uniques ; rattachement niveau/parcours.
- **RG03 & RG04** : Les messages envoyés sont immuables. Chaque utilisateur dispose de son propre état de boîte (`boite` : `lu`, `favori`, `dossier`).
- **RG06** : Les destinataires en copie cachée (`Bcc`) ne sont visibles que par l'expéditeur et le destinataire concerné.
- **RG07 & RG08** : Listes de diffusion automatiques (calculées selon les critères de rôle/niveau/parcours) et manuelles. Restriction pour les étudiants (uniquement si `ouverte_etudiants = True`).
- **RG09** : Sécurité des pièces jointes : limite de 10 Mo par fichier, extensions exécutables interdites (`.exe`, `.bat`, `.cmd`, `.js`, `.vbs`).
- **RG10** : Traçabilité et audit automatique (`journal`) lors des diffusions massives (> 50 destinataires) ou annonces officielles.
- **RG12 & RG13** : Mot de passe sécurisé, inscription en ligne avec statut « en attente » validé par l'administration.

---

## 3. Installation et exécution

Deux modes d'installation sont disponibles : **Docker** (recommandé pour la production et le développement intégré) et **manuel** (recommandé pour le développement backend seul).

---

### 🐳 Mode Docker — recommandé

#### Prérequis
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 24 (ou Docker Engine + Compose plugin)

#### Démarrage en 3 commandes

```bash
# Depuis la racine du projet (eni-mailing/)

# 1. Copier et ajuster les variables d'environnement (une seule fois)
cp backend/.env.example backend/.env

# 2. Construire et démarrer tous les services
docker compose up -d

# 3. Suivre les logs de démarrage de l'API
docker compose logs -f api
```

> **Ce que fait `docker compose up` :**
> 1. Démarre un conteneur **PostgreSQL 16** (`db`) avec la base `eni_mailing`
> 2. Attend que PostgreSQL soit prêt (healthcheck `pg_isready`)
> 3. Applique les migrations **Alembic** (`alembic upgrade head`)
> 4. Peuple la base avec les données de démo (`python -m app.db.init_db`)
> 5. Lance **Uvicorn** sur le port `8000`

#### URLs disponibles après démarrage

| URL | Description |
|-----|-------------|
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/api/docs` | Documentation Swagger interactive |
| `http://localhost:8000/api/openapi.json` | Spécification OpenAPI |
| `http://localhost:4200` | Frontend Angular (si démarré séparément) |

#### Commandes Docker utiles

```bash
# Arrêter les services (données conservées)
docker compose down

# Arrêter ET supprimer les données PostgreSQL
docker compose down -v

# Rebuilder l'image API après modification du code
docker compose up -d --build api

# Accéder au shell du conteneur API
docker compose exec api sh

# Accéder à PostgreSQL via psql
docker compose exec db psql -U eni_user -d eni_mailing
```

#### Variables d'environnement PostgreSQL

```env
POSTGRES_DB=eni_mailing
POSTGRES_USER=eni_user
POSTGRES_PASSWORD=change_this_password
DATABASE_URL=postgresql+psycopg://eni_user:change_this_password@db:5432/eni_mailing
```

> ⚠️ **Production** : Modifier `POSTGRES_PASSWORD` et `SECRET_KEY` dans `backend/.env` avant tout déploiement.

---

### 🛠 Mode manuel — développement local

#### Prérequis
- Python 3.11+
- PostgreSQL 14+ en local **ou** utiliser SQLite (pour les tests uniquement)

#### 3.1 Environnement virtuel Python

```bash
# Depuis backend/

# Création
python -m venv .venv

# Activation (Linux / WSL / macOS)
source .venv/bin/activate

# Activation (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Installation des dépendances
pip install -r requirements.txt
```

#### 3.2 Variables d'environnement

```bash
cp .env.example .env
```

Modifier `.env` pour pointer vers votre PostgreSQL local :

```env
DATABASE_URL=postgresql+psycopg://eni_user:change_this_password@localhost:5432/eni_mailing
SECRET_KEY=dev_secret_key_change_in_production_super_secure_hash_12345
```

#### 3.3 Migrations et données initiales

```bash
# Appliquer les migrations Alembic
alembic upgrade head

# Peupler la base avec les données de démo
python -m app.db.init_db
```

#### 3.4 Démarrage du serveur

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### Comptes de démo préconfigurés

| Rôle | Email | Mot de passe |
|------|-------|-------------|
| Administrateur | `admin@eni.mg` | `Admin@2026` |
| Personnel (Scolarité) | `scolarite@eni.mg` | `Eni@2026` |
| Personnel (Direction) | `direction@eni.mg` | `Eni@2026` |
| Enseignant | `jean.rakotomalala@eni.mg` | `Eni@2026` |
| Étudiant | `toky.rabe@eni.mg` | `Eni@2026` |

---

## 4. Tests automatisés

La suite de tests s'exécute en mémoire vive (SQLite) **sans PostgreSQL ni Docker** :

```bash
# Depuis backend/
pytest

# Avec détails
pytest -v

# Un module spécifique
pytest tests/test_auth.py -v
```

Résultat attendu :
```
25 passed in ~4s
```

Les tests couvrent :
- **Authentification** (`test_auth.py`) : login, token JWT, consultation/mise à jour du profil, inscription.
- **Utilisateurs** (`test_users.py`) : pagination, recherche, création admin, suspension de compte.
- **Messagerie** (`test_mails.py`) : envoi, brouillons, lecture, compteurs de dossiers, corbeille, favoris.
- **Listes de diffusion** (`test_groups.py`) : listes automatiques/manuelles, droits enseignants/étudiants.
- **Modèles** (`test_templates.py`) : modèles d'annonces avec variables `{{...}}`.
- **Administration** (`test_admin.py`) : statistiques d'activité, journal d'audit.

