"""Diagnostic de la configuration SMTP (lit le même .env que l'API).

Utilisation, depuis le dossier backend/ :
    python scripts/check_smtp.py                       -> teste connexion, STARTTLS et authentification
    python scripts/check_smtp.py destinataire@gmail.com -> envoie en plus un e-mail de test

Chaque étape est affichée : la première qui échoue indique la cause (réseau, port, TLS, identifiants).
"""
import socket
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402


def step(label: str) -> None:
    print(f"\n--- {label}")


def main() -> int:
    recipient = sys.argv[1] if len(sys.argv) > 1 else None
    host, port = settings.SMTP_HOST, settings.SMTP_PORT

    step("Configuration lue dans .env")
    print(f"SMTP_HOST      = {host!r}")
    print(f"SMTP_PORT      = {port}")
    print(f"SMTP_TLS       = {settings.SMTP_TLS}")
    print(f"SMTP_USERNAME  = {settings.SMTP_USERNAME!r}")
    print(f"SMTP_PASSWORD  = {'(' + str(len(settings.SMTP_PASSWORD)) + ' caractères)' if settings.SMTP_PASSWORD else '(vide)'}")
    print(f"SMTP_FROM_EMAIL= {settings.SMTP_FROM_EMAIL!r}")
    if not host:
        print("\nSMTP_HOST est vide : aucun e-mail n'est envoyé (mode simulation).")
        return 1
    if settings.SMTP_USERNAME and settings.SMTP_FROM_EMAIL != settings.SMTP_USERNAME:
        print("\nATTENTION : SMTP_FROM_EMAIL diffère de SMTP_USERNAME (Gmail/Outlook réécrivent ou refusent l'expéditeur).")
    if " " in (settings.SMTP_PASSWORD or ""):
        print("\nATTENTION : le mot de passe contient des espaces (mot de passe d'application Gmail : retirez-les).")

    step(f"1. Connexion TCP à {host}:{port}")
    try:
        socket.create_connection((host, port), timeout=10).close()
        print("OK : le port est joignable.")
    except OSError as e:
        print(f"ÉCHEC : {type(e).__name__}: {e}")
        print("-> pare-feu, antivirus (protection e-mail), réseau ou mauvais port.")
        return 1

    server = None
    try:
        step("2. Dialogue SMTP" + (" (SSL implicite)" if port == 465 else ""))
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=20, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(host, port, timeout=20)
        server.set_debuglevel(1)
        print("Bannière :", server.noop())
        server.ehlo()
        if port != 465 and settings.SMTP_TLS:
            step("3. STARTTLS")
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            print("OK : connexion chiffrée.")
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            step("4. Authentification")
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            print("OK : identifiants acceptés.")
        if recipient:
            step(f"5. Envoi d'un e-mail de test à {recipient}")
            msg = EmailMessage()
            msg["Subject"] = "Test SMTP — ENI Mailing"
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["To"] = recipient
            msg.set_content("Si vous lisez ce message, la configuration SMTP fonctionne.")
            server.send_message(msg)
            print("OK : e-mail accepté par le serveur.")
        print("\nRésultat : la configuration SMTP fonctionne.")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"\nÉCHEC : {type(e).__name__}: {e}")
        if isinstance(e, smtplib.SMTPServerDisconnected):
            print("-> le serveur a coupé la connexion : mauvais port/TLS (587 + SMTP_TLS=True, ou 465), "
                  "antivirus/pare-feu qui intercepte le TLS, ou réseau qui bloque ce port.")
        elif isinstance(e, smtplib.SMTPAuthenticationError):
            print("-> identifiants refusés : Gmail exige un « mot de passe d'application » (validation en 2 étapes activée).")
        return 1
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:  # noqa: BLE001
                pass


if __name__ == "__main__":
    sys.exit(main())
