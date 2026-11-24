def test_login_success(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@eni.mg", "password": "Admin@2026"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"]["email"] == "admin@eni.mg"
    assert data["user"]["role"] == "ADMIN"


def test_login_failure(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@eni.mg", "password": "WrongPassword"},
    )
    assert response.status_code == 401


def test_get_me(client, admin_headers):
    response = client.get("/api/auth/me", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@eni.mg"
    assert data["firstName"] == "Hery"


def test_update_me(client, student_headers):
    response = client.put(
        "/api/auth/me",
        json={"phone": "034 99 999 99", "signature": "Signature Toky"},
        headers=student_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "034 99 999 99"
    assert data["signature"] == "Signature Toky"


def test_register_pending_user(client):
    response = client.post(
        "/api/auth/register",
        json={
            "role": "ETUDIANT",
            "firstName": "Tahina",
            "lastName": "Ravelo",
            "email": "tahina.ravelo@eni.mg",
            "emailVerification": "tahina.perso@gmail.com",
            "phone": "034 11 222 33",
            "matricule": "ENI-2026-9999",
            "password": "Password1234!",
            "level": "L1",
            "track": "IG",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "tahina.ravelo@eni.mg"
    assert data["pending"] is True

