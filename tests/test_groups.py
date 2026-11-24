def test_get_groups(client, student_headers):
    response = client.get("/api/groups", headers=student_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 6
    group_names = [g["name"] for g in data]
    assert "Tous les étudiants" in group_names


def test_get_group_detail(client, student_headers):
    response = client.get("/api/groups/5", headers=student_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 5
    assert data["name"] == "Club Dev ENI"
    assert "members" in data
    assert data["memberCount"] >= 5


def test_create_and_delete_group(client, teacher_headers):
    payload = {
        "name": "Nouveau Groupe Test",
        "address": "test-group@eni.mg",
        "description": "Groupe de test automatique",
        "type": "MANUELLE",
        "openToStudents": True,
        "memberIds": [7, 8],
    }
    create_resp = client.post("/api/groups", json=payload, headers=teacher_headers)
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/groups/{group_id}", headers=teacher_headers)
    assert del_resp.status_code == 204


def test_student_cannot_create_group(client, student_headers):
    payload = {
        "name": "Groupe Non Autorise",
        "address": "unauthorized@eni.mg",
        "type": "MANUELLE",
        "openToStudents": False,
        "memberIds": [],
    }
    resp = client.post("/api/groups", json=payload, headers=student_headers)
    assert resp.status_code == 403

