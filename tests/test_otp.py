import pytest
from app.models.user import Utilisateur
from app.models.otp import OtpCode
from app.services.email_service import email_service
from app.services.otp_service import otp_service


def test_register_creates_unverified_user_and_generates_otp(client, db_session):
    payload = {
        "matricule": "ENI-TEST-OTP-01",
        "firstName": "Fitahiana",
        "lastName": "Rasoa",
        "email": "fitahiana.rasoa@eni.mg",
        "emailVerification": "fitahiana.perso@gmail.com",
        "phone": "+261 34 11 222 33",
        "password": "StrongPassword@2026",
        "role": "ETUDIANT",
        "level": "L3",
        "track": "GB",
        "enrollmentYear": "2025-2026",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "fitahiana.rasoa@eni.mg"
    assert data["is_verified"] is False
    assert data["pending"] is True

    # Vérification en base de données
    user = db_session.query(Utilisateur).filter_by(email="fitahiana.rasoa@eni.mg").first()
    assert user is not None
    assert user.is_verified is False
    assert user.email_verification == "fitahiana.perso@gmail.com"
    assert user.email_verification_verifie is False

    # Un code OTP doit être créé
    otp = db_session.query(OtpCode).filter_by(user_id=user.id, purpose="REGISTER", is_used=False).first()
    assert otp is not None
    assert otp.attempts == 0

    # Le code est envoyé à l'e-mail externe de vérification (pas à l'adresse ENI)
    assert email_service.get_last_code_for_testing("fitahiana.rasoa@eni.mg") is None
    sent_code = email_service.get_last_code_for_testing("fitahiana.perso@gmail.com")
    assert sent_code is not None
    assert len(sent_code) == 6
    assert otp_service.verify_hash(sent_code, user.id, otp.code_hash) is True


def test_login_blocked_if_email_not_verified(client, db_session):
    # L'utilisateur fitahiana créé au test précédent n'est pas vérifié
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "fitahiana.rasoa@eni.mg", "password": "StrongPassword@2026"},
    )
    assert login_resp.status_code == 403
    assert "vérifiée" in login_resp.json()["detail"].lower()


def test_verify_otp_with_incorrect_code(client, db_session):
    resp = client.post(
        "/api/auth/verify-otp",
        json={"email": "fitahiana.rasoa@eni.mg", "code": "000000", "purpose": "REGISTER"},
    )
    assert resp.status_code == 400
    assert "incorrect" in resp.json()["detail"].lower()

    # Tentative enregistrée
    user = db_session.query(Utilisateur).filter_by(email="fitahiana.rasoa@eni.mg").first()
    otp = db_session.query(OtpCode).filter_by(user_id=user.id, purpose="REGISTER", is_used=False).first()
    assert otp.attempts == 1


def test_verify_otp_success(client, db_session):
    code = email_service.get_last_code_for_testing("fitahiana.perso@gmail.com")
    resp = client.post(
        "/api/auth/verify-otp",
        json={"email": "fitahiana.rasoa@eni.mg", "code": code, "purpose": "REGISTER"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Vérification en base
    user = db_session.query(Utilisateur).filter_by(email="fitahiana.rasoa@eni.mg").first()
    assert user.is_verified is True
    assert user.email_verification_verifie is True

    # Le code est maintenant consommé
    used_otp = db_session.query(OtpCode).filter_by(user_id=user.id, purpose="REGISTER", is_used=True).first()
    assert used_otp is not None


def test_resend_otp_cooldown_limit(client, db_session):
    # Création d'un autre utilisateur pour tester le renvoi
    client.post(
        "/api/auth/register",
        json={
            "matricule": "ENI-TEST-OTP-02",
            "firstName": "Andry",
            "lastName": "Rajaona",
            "email": "andry.rajaona@eni.mg",
            "emailVerification": "andry.perso@gmail.com",
            "phone": "+261 34 55 666 77",
            "password": "StrongPassword@2026",
            "role": "ETUDIANT",
            "level": "L2",
            "track": "IG",
            "enrollmentYear": "2025-2026",
        },
    )

    # Demande immédiate de renvoi -> Cooldown actif (429)
    resend_resp = client.post(
        "/api/auth/resend-otp",
        json={"email": "andry.rajaona@eni.mg", "purpose": "REGISTER"},
    )
    assert resend_resp.status_code == 429
    assert "patienter" in resend_resp.json()["detail"].lower()


def test_forgot_password_and_reset_flow(client, db_session):
    # Prérequis : l'admin possède un e-mail externe de vérification déjà validé
    admin = db_session.query(Utilisateur).filter_by(email="admin@eni.mg").first()
    admin.email_verification = "admin.perso@gmail.com"
    admin.email_verification_verifie = True
    db_session.commit()

    # 1. Demande de réinitialisation pour le compte admin (admin@eni.mg)
    forgot_resp = client.post(
        "/api/auth/forgot-password",
        json={"email": "admin@eni.mg"},
    )
    assert forgot_resp.status_code == 200
    assert forgot_resp.json()["success"] is True

    reset_code = email_service.get_last_code_for_testing("admin.perso@gmail.com")
    assert reset_code is not None

    # 2. Validation de l'OTP de réinitialisation
    verify_resp = client.post(
        "/api/auth/verify-reset-otp",
        json={"email": "admin@eni.mg", "code": reset_code},
    )
    assert verify_resp.status_code == 200
    reset_token = verify_resp.json()["resetToken"]
    assert reset_token is not None

    # 3. Réinitialisation avec le token et le nouveau mot de passe (RG12 conforme)
    new_password = "BrandNewAdminPass@2026"
    reset_resp = client.post(
        "/api/auth/reset-password",
        json={
            "email": "admin@eni.mg",
            "reset_token": reset_token,
            "new_password": new_password,
        },
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["success"] is True

    # 4. Connexion réussie avec le nouveau mot de passe
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "admin@eni.mg", "password": new_password},
    )
    assert login_resp.status_code == 200
    assert "token" in login_resp.json()


def test_forgot_password_generic_message_on_unknown_email(client):
    resp = client.post(
        "/api/auth/forgot-password",
        json={"email": "nonexistent.user@eni.mg"},
    )
    # Ne doit pas lever 404 pour empêcher l'énumération d'adresses
    assert resp.status_code == 200
    assert resp.json()["success"] is True



def test_register_rejects_same_verification_email_as_eni_email(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "matricule": "ENI-TEST-OTP-03",
            "firstName": "Same",
            "lastName": "Mail",
            "email": "same.mail@eni.mg",
            "emailVerification": "Same.Mail@eni.mg",
            "phone": "+261 34 00 000 03",
            "password": "StrongPassword@2026",
            "role": "ETUDIANT",
            "level": "L1",
            "track": "GB",
        },
    )
    assert resp.status_code == 422


def test_register_duplicate_verification_email_conflict(client):
    base = {
        "firstName": "Dup",
        "lastName": "Verif",
        "phone": "+261 34 00 000 04",
        "password": "StrongPassword@2026",
        "role": "ETUDIANT",
        "level": "L1",
        "track": "GB",
        "emailVerification": "dup.verif@gmail.com",
    }
    first = client.post(
        "/api/auth/register",
        json={**base, "matricule": "ENI-TEST-OTP-04", "email": "dup.un@eni.mg"},
    )
    assert first.status_code == 201
    second = client.post(
        "/api/auth/register",
        json={**base, "matricule": "ENI-TEST-OTP-05", "email": "dup.deux@eni.mg"},
    )
    assert second.status_code == 409


def test_forgot_password_without_verified_external_email_sends_nothing(client):
    # Compte du jeu de données sans e-mail externe vérifié
    resp = client.post(
        "/api/auth/forgot-password",
        json={"email": "scolarite@eni.mg"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert email_service.get_last_code_for_testing("scolarite@eni.mg") is None
