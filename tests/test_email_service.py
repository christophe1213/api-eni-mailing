from unittest.mock import MagicMock

import pytest

from app.core.config import settings
from app.services import email_service as email_module


@pytest.fixture
def smtp(monkeypatch):
    """Remplace smtplib par des doubles et configure un serveur SMTP fictif."""
    fake = MagicMock()
    monkeypatch.setattr(email_module, "smtplib", fake)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_USERNAME", "robot@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "secret")
    monkeypatch.setattr(settings, "SMTP_TLS", True)
    return fake


def _send():
    return email_module.email_service._send_smtp(
        recipient_email="dest@gmail.com", subject="Sujet", html_content="<p>x</p>", plain_text="x"
    )


def test_port_587_uses_starttls(smtp, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    assert _send() is True
    smtp.SMTP.assert_called_once()
    smtp.SMTP_SSL.assert_not_called()
    server = smtp.SMTP.return_value
    server.starttls.assert_called_once()
    server.login.assert_called_once_with("robot@example.com", "secret")
    server.sendmail.assert_called_once()
    server.quit.assert_called_once()


def test_port_465_uses_implicit_ssl(smtp, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_PORT", 465)
    assert _send() is True
    smtp.SMTP_SSL.assert_called_once()
    smtp.SMTP.assert_not_called()
    server = smtp.SMTP_SSL.return_value
    server.starttls.assert_not_called()
    server.sendmail.assert_called_once()
    server.quit.assert_called_once()


def test_failure_returns_false_and_closes_connection(smtp, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    server = smtp.SMTP.return_value
    server.login.side_effect = RuntimeError("boom")
    assert _send() is False
    server.sendmail.assert_not_called()
    server.quit.assert_called_once()
