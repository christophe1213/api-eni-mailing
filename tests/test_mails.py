def test_get_folder_counts(client, student_headers):
    response = client.get("/api/mails/counts", headers=student_headers)
    assert response.status_code == 200
    data = response.json()
    assert "inbox" in data
    assert "sent" in data
    assert "drafts" in data
    assert "trash" in data


def test_send_mail_and_receive(client, teacher_headers, student_headers):
    # Enseignant (id=4) envoie un message à Étudiant Toky (id=7)
    compose_payload = {
        "subject": "Sujet de test",
        "body": "Ceci est un corps de message pour test unitaire.",
        "priority": "NORMALE",
        "to": [7],
        "cc": [],
        "bcc": [],
        "groupIds": [],
        "attachmentIds": [],
        "isAnnouncement": False,
        "draft": False,
    }
    send_resp = client.post("/api/mails", json=compose_payload, headers=teacher_headers)
    assert send_resp.status_code == 201
    mail_data = send_resp.json()
    assert mail_data["subject"] == "Sujet de test"
    mail_id = mail_data["id"]

    # Étudiant consulte sa boîte de réception
    inbox_resp = client.get("/api/mails?folder=inbox", headers=student_headers)
    assert inbox_resp.status_code == 200
    inbox_data = inbox_resp.json()
    mail_ids = [m["id"] for m in inbox_data["items"]]
    assert mail_id in mail_ids

    # Étudiant lit le message
    detail_resp = client.get(f"/api/mails/{mail_id}", headers=student_headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["body"] == "Ceci est un corps de message pour test unitaire."
    assert detail_data["read"] is True


def test_save_and_update_draft(client, student_headers):
    # Enregistrer un brouillon
    draft_payload = {
        "subject": "Brouillon test",
        "body": "Texte préliminaire...",
        "priority": "NORMALE",
        "to": [4],
        "draft": True,
    }
    resp1 = client.post("/api/mails", json=draft_payload, headers=student_headers)
    assert resp1.status_code == 201
    draft_id = resp1.json()["id"]

    # Mettre à jour le brouillon
    update_payload = {
        "subject": "Brouillon mis à jour",
        "body": "Texte finalisé.",
        "priority": "HAUTE",
        "to": [4],
        "draft": True,
    }
    resp2 = client.put(f"/api/mails/{draft_id}", json=update_payload, headers=student_headers)
    assert resp2.status_code == 200
    assert resp2.json()["subject"] == "Brouillon mis à jour"


def test_patch_and_delete_mail(client, student_headers):
    # Récupérer un message de l'inbox
    inbox = client.get("/api/mails?folder=inbox", headers=student_headers).json()
    if inbox["items"]:
        mid = inbox["items"][0]["id"]
        # Marquer comme favori
        patch_resp = client.patch(f"/api/mails/{mid}", json={"starred": True}, headers=student_headers)
        assert patch_resp.status_code == 200
        assert patch_resp.json()["starred"] is True

        # Déplacer en corbeille
        del_resp = client.delete(f"/api/mails/{mid}", headers=student_headers)
        assert del_resp.status_code == 204

