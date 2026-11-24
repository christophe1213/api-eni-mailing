import io

import pytest
from PIL import Image

from app.core.config import settings


@pytest.fixture(autouse=True)
def avatar_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AVATAR_DIR", str(tmp_path / "avatars"))


def make_image(fmt="PNG", size=(600, 400), color=(200, 30, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, fmt)
    return buf.getvalue()


def upload(client, headers, data, name="photo.png", mime="image/png"):
    return client.post(
        "/api/auth/me/avatar", files={"file": (name, data, mime)}, headers=headers
    )


def test_upload_avatar_returns_user_with_url(client, student_headers):
    res = upload(client, student_headers, make_image())
    assert res.status_code == 200
    url = res.json()["avatarUrl"]
    assert url.startswith("/api/users/") and "/avatar?v=" in url


def test_avatar_is_served_publicly_as_square_jpeg(client, student_headers):
    url = upload(client, student_headers, make_image()).json()["avatarUrl"]
    res = client.get(url)  # sans en-tête Authorization (balise <img>)
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/jpeg"
    img = Image.open(io.BytesIO(res.content))
    assert img.size == (settings.AVATAR_PIXELS, settings.AVATAR_PIXELS)


def test_avatar_url_in_me_and_user_summaries(client, student_headers):
    url = upload(client, student_headers, make_image()).json()["avatarUrl"]
    me = client.get("/api/auth/me", headers=student_headers).json()
    assert me["avatarUrl"] == url


def test_upload_rejects_non_image(client, student_headers):
    res = upload(client, student_headers, b"not an image", "x.png", "image/png")
    assert res.status_code == 422


def test_upload_rejects_unsupported_format(client, student_headers):
    res = upload(client, student_headers, make_image("GIF"), "x.gif", "image/gif")
    assert res.status_code == 422


def test_upload_rejects_too_large(client, student_headers, monkeypatch):
    monkeypatch.setattr(settings, "MAX_AVATAR_SIZE", 100)
    res = upload(client, student_headers, make_image())
    assert res.status_code == 422


def test_upload_requires_auth(client):
    res = client.post(
        "/api/auth/me/avatar", files={"file": ("a.png", make_image(), "image/png")}
    )
    assert res.status_code == 401


def test_delete_avatar(client, student_headers):
    url = upload(client, student_headers, make_image()).json()["avatarUrl"]
    res = client.delete("/api/auth/me/avatar", headers=student_headers)
    assert res.status_code == 200
    assert res.json()["avatarUrl"] is None
    assert client.get(url).status_code == 404


def test_get_avatar_unknown_user_404(client):
    assert client.get("/api/users/99999/avatar").status_code == 404
