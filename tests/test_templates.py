def test_get_templates(client, admin_headers):
    response = client.get("/api/templates", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3


def test_create_and_delete_template(client, admin_headers):
    payload = {
        "title": "Modèle Test",
        "category": "Examens",
        "subject": "Sujet {{nom}}",
        "body": "Bonjour {{nom}}, votre note est {{note}}.",
    }
    create_resp = client.post("/api/templates", json=payload, headers=admin_headers)
    assert create_resp.status_code == 201
    tid = create_resp.json()["id"]

    del_resp = client.delete(f"/api/templates/{tid}", headers=admin_headers)
    assert del_resp.status_code == 204


def test_student_cannot_access_templates(client, student_headers):
    resp = client.get("/api/templates", headers=student_headers)
    assert resp.status_code == 403

