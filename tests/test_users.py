def test_get_users_list(client, student_headers):
    response = client.get("/api/users", headers=student_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 14
    assert len(data["items"]) > 0


def test_get_user_by_id(client, student_headers):
    response = client.get("/api/users/1", headers=student_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["email"] == "admin@eni.mg"


def test_admin_create_user(client, admin_headers):
    response = client.post(
        "/api/users",
        json={
            "matricule": "ENI-TEST-001",
            "firstName": "Test",
            "lastName": "User",
            "email": "test.user@eni.mg",
            "role": "ETUDIANT",
            "level": "L2",
            "track": "GB",
            "active": True,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test.user@eni.mg"
    assert data["matricule"] == "ENI-TEST-001"


def test_student_cannot_create_user(client, student_headers):
    response = client.post(
        "/api/users",
        json={
            "matricule": "ENI-TEST-002",
            "firstName": "Hacker",
            "lastName": "User",
            "email": "hacker@eni.mg",
            "role": "ETUDIANT",
            "active": True,
        },
        headers=student_headers,
    )
    assert response.status_code == 403


def test_admin_toggle_active(client, admin_headers):
    response = client.patch(
        "/api/users/7/active",
        json={"active": False},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active"] is False

    # Restaurer actif
    client.patch("/api/users/7/active", json={"active": True}, headers=admin_headers)

