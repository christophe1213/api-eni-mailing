def test_admin_stats(client, admin_headers):
    response = client.get("/api/admin/stats", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "messagesSent" in data
    assert "groups" in data
    assert "activity" in data
    assert "topSenders" in data
    assert data["users"]["total"] >= 14


def test_admin_audit_logs(client, admin_headers):
    response = client.get("/api/admin/logs", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_student_cannot_access_admin_stats(client, student_headers):
    resp = client.get("/api/admin/stats", headers=student_headers)
    assert resp.status_code == 403

