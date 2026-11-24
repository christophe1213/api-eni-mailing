#!/bin/sh
# ============================================================
# Entrypoint du conteneur API
# 1. Attendre que PostgreSQL soit prêt (healthcheck Docker)
# 2. Appliquer les migrations Alembic
# 3. Peupler la base avec les données initiales (idempotent)
# 4. Démarrer l'application Uvicorn
# ============================================================
set -e

echo "▶ Application des migrations Alembic..."
alembic upgrade head

echo "▶ Initialisation des données de base..."
python -m app.db.init_db

echo "▶ Démarrage du serveur Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

