# Utilisateurs de test : 1 = admin, 2 = personnel, 4 = enseignant, 7 = étudiant, 8 = étudiant
BASE = "/api/users/{uid}/contacts"


def _url(uid, contact_user_id=None):
    return BASE.format(uid=uid) + (
        f"/{contact_user_id}" if contact_user_id is not None else ""
    )


def _cleanup(client, uid, headers):
    response = client.get(_url(uid) + "?pageSize=100", headers=headers)
    assert response.status_code == 200
    for user in response.json()["items"]:
        client.delete(_url(uid, user["id"]), headers=headers)


def test_requires_authentication(client):
    assert client.get(_url(7)).status_code == 401


def test_add_list_remove_for_every_role(
    client, admin_headers, teacher_headers, student_headers
):
    for uid, headers in ((1, admin_headers), (4, teacher_headers), (7, student_headers)):
        _cleanup(client, uid, headers)
        created = client.post(_url(uid), json={"contactUserId": 8}, headers=headers)
        assert created.status_code == 201
        body = created.json()
        assert body["id"] == 8
        assert body["email"] == "nomena.rakotoarisoa@eni.mg"
        assert body["firstName"] == "Nomena"

        listing_response = client.get(_url(uid), headers=headers)
        assert listing_response.status_code == 200
        listing = listing_response.json()
        assert listing["total"] == 1
        assert listing["items"][0]["id"] == 8
        assert listing["items"][0]["email"] == body["email"]
        assert "user" not in listing["items"][0]

        assert client.delete(_url(uid, body["id"]), headers=headers).status_code == 204
        assert client.get(_url(uid), headers=headers).json()["total"] == 0
        assert client.delete(_url(uid, body["id"]), headers=headers).status_code == 404


def test_delete_uses_contact_user_id_not_contact_row_id(client, student_headers):
    _cleanup(client, 7, student_headers)
    for contact_user_id in (8, 9):
        response = client.post(
            _url(7), json={"contactUserId": contact_user_id}, headers=student_headers
        )
        assert response.status_code == 201

    assert client.delete(_url(7, 8), headers=student_headers).status_code == 204
    remaining = client.get(_url(7), headers=student_headers).json()["items"]
    assert [user["id"] for user in remaining] == [9]
    _cleanup(client, 7, student_headers)


def test_cannot_add_self_twice_or_unknown(client, student_headers):
    _cleanup(client, 7, student_headers)
    assert client.post(_url(7), json={"contactUserId": 7}, headers=student_headers).status_code == 400
    assert client.post(_url(7), json={"contactUserId": 99999}, headers=student_headers).status_code == 404
    assert client.post(_url(7), json={"contactUserId": 8}, headers=student_headers).status_code == 201
    assert client.post(_url(7), json={"contactUserId": 8}, headers=student_headers).status_code == 409
    assert client.post(_url(7), json={}, headers=student_headers).status_code == 422
    _cleanup(client, 7, student_headers)


def test_other_users_book_is_404_not_403(client, admin_headers, student_headers):
    _cleanup(client, 1, admin_headers)
    assert client.post(
        _url(1), json={"contactUserId": 2}, headers=admin_headers
    ).status_code == 201

    # L'étudiant (id 7) vise le carnet de l'admin (id 1) : toujours 404.
    assert client.get(_url(1), headers=student_headers).status_code == 404
    assert client.post(_url(1), json={"contactUserId": 8}, headers=student_headers).status_code == 404
    assert client.delete(_url(1, 2), headers=student_headers).status_code == 404

    # Même avec son propre userId, il ne peut pas supprimer l'entrée de l'admin.
    assert client.delete(_url(7, 2), headers=student_headers).status_code == 404

    # Rien n'a été modifié côté admin.
    assert client.get(_url(1), headers=admin_headers).json()["total"] == 1
    _cleanup(client, 1, admin_headers)


def test_same_user_can_be_contact_of_several_people(client, admin_headers, student_headers):
    _cleanup(client, 1, admin_headers)
    _cleanup(client, 7, student_headers)
    assert client.post(_url(1), json={"contactUserId": 2}, headers=admin_headers).status_code == 201
    assert client.post(_url(7), json={"contactUserId": 2}, headers=student_headers).status_code == 201
    _cleanup(client, 1, admin_headers)
    _cleanup(client, 7, student_headers)


def test_search_and_pagination(client, student_headers):
    _cleanup(client, 7, student_headers)
    for target in (2, 4, 8, 9):
        assert client.post(_url(7), json={"contactUserId": target}, headers=student_headers).status_code == 201

    assert client.get(_url(7) + "?q=rakoto", headers=student_headers).json()["total"] == 2  # Rakotomalala, Rakotoarisoa
    res = client.get(_url(7) + "?q=scolarite@eni", headers=student_headers).json()
    assert [user["id"] for user in res["items"]] == [2]
    assert client.get(_url(7) + "?q=%25", headers=student_headers).json()["total"] == 0

    res = client.get(_url(7) + "?page=2&pageSize=3", headers=student_headers).json()
    assert res["total"] == 4 and len(res["items"]) == 1 and res["page"] == 2
    _cleanup(client, 7, student_headers)


def test_exists_endpoint(client, student_headers):
    _cleanup(client, 7, student_headers)
    assert client.get(_url(7, 8) + "/exists", headers=student_headers).json() == {"exists": False}
    assert client.post(_url(7), json={"contactUserId": 8}, headers=student_headers).status_code == 201
    assert client.get(_url(7, 8) + "/exists", headers=student_headers).json() == {"exists": True}
    _cleanup(client, 7, student_headers)


def test_model_constraints():
    from app.models.contact import Contact

    for col in ("utilisateur_id", "contact_utilisateur_id"):
        fk = next(iter(Contact.__table__.c[col].foreign_keys))
        assert fk.ondelete == "CASCADE"
