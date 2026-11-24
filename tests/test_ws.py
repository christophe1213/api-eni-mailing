import pytest
from app.api import deps
from tests.conftest import TestingSessionLocal


@pytest.fixture(autouse=True)
def _ws_db(monkeypatch):
    # get_user_from_token ouvre sa propre session : on la pointe vers la base de test
    monkeypatch.setattr(deps, "SessionLocal", TestingSessionLocal)


def test_ws_rejects_bad_token(client):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/ws?token=nimportequoi"):
            pass


def test_ws_receives_new_mail(client, teacher_headers, student_token):
    with client.websocket_connect(f"/api/ws?token={student_token}") as ws:
        resp = client.post(
            "/api/mails",
            json={"subject": "RT", "body": "temps réel", "to": [7], "draft": False},
            headers=teacher_headers,
        )
        assert resp.status_code == 201
        event = ws.receive_json()
        assert event["type"] == "mail.new"
        assert event["mailId"] == resp.json()["id"]
        assert event["subject"] == "RT"
        assert event["from"]


def test_ws_counts_changed_on_patch(client, student_headers, student_token):
    inbox = client.get("/api/mails?folder=inbox", headers=student_headers).json()
    mid = inbox["items"][0]["id"]
    with client.websocket_connect(f"/api/ws?token={student_token}") as ws:
        client.patch(f"/api/mails/{mid}", json={"starred": True}, headers=student_headers)
        assert ws.receive_json() == {"type": "counts.changed"}


def test_ws_ping_pong(client, student_token):
    with client.websocket_connect(f"/api/ws?token={student_token}") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"
