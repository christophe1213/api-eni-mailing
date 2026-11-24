import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("eni_mailing.email")


class EmailService:
    def __init__(self):
        # En mode test ou développement sans SMTP, mémorise le dernier code envoyé
        self._dev_sent_codes: dict[str, str] = {}

    def get_last_code_for_testing(self, email: str) -> Optional[str]:
        """Méthode utilitaire pour les tests automatisés."""
        return self._dev_sent_codes.get(email.lower())

    def send_otp_email(
        self,
        *,
        recipient_email: str,
        recipient_name: Optional[str] = None,
        code: str,
        purpose: str = "REGISTER",
    ) -> bool:
        """
        Envoie un e-mail avec le code OTP de manière sécurisée.
        Ne logue JAMAIS le code OTP en clair dans les logs de production.
        """
        # Mémorisation pour tests / dev
        self._dev_sent_codes[recipient_email.lower()] = code

        name_display = recipient_name or recipient_email.split("@")[0]
        
        if purpose == "PASSWORD_RESET":
            subject = "Réinitialisation de votre mot de passe — ENI Mail"
            title = "Réinitialisation de mot de passe"
            message_intro = (
                "Vous avez demandé la réinitialisation de votre mot de passe pour votre compte ENI Mail. "
                "Voici votre code de sécurité à usage unique :"
            )
        else:
            subject = "Vérification de votre adresse e-mail — ENI Mail"
            title = "Vérification de votre compte"
            message_intro = (
                "Bienvenue sur la plateforme ENI Mail ! Pour valider votre adresse e-mail de vérification "
                "et sécuriser votre compte, veuillez utiliser le code de vérification suivant :"
            )

        html_content = self._render_otp_template(
            title=title,
            recipient_name=name_display,
            message_intro=message_intro,
            code=code,
            validity_minutes=settings.OTP_EXPIRE_MINUTES,
        )

        plain_text = (
            f"Bonjour {name_display},\n\n"
            f"{message_intro}\n\n"
            f"Code de vérification : {code}\n"
            f"Ce code expire dans {settings.OTP_EXPIRE_MINUTES} minutes.\n\n"
            f"Ne partagez jamais ce code. Si vous n'avez pas fait cette demande, ignorez ce message.\n\n"
            f"--\nÉcole Nationale d'Informatique (ENI)"
        )

        return self._send_smtp(
            recipient_email=recipient_email,
            subject=subject,
            html_content=html_content,
            plain_text=plain_text,
        )

    def _send_smtp(
        self,
        *,
        recipient_email: str,
        subject: str,
        html_content: str,
        plain_text: str,
    ) -> bool:
        """Gère l'envoi réel via SMTP ou le fallback sécurisé."""
        if not settings.SMTP_HOST:
            # Mode développement / tests : SMTP non configuré
            logger.info(
                "Envoi d'e-mail simulé pour %s (Sujet: '%s'). Configuration SMTP absente.",
                recipient_email,
                subject,
            )
            return True

        server: Optional[smtplib.SMTP] = None
        try:
            msg = MIMEMultipart("alternative")
            sender = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = recipient_email

            msg.attach(MIMEText(plain_text, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            if settings.SMTP_PORT == 465:
                # Port 465 = SSL implicite (la connexion est chiffrée dès le départ, pas de STARTTLS)
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20)
                server.ehlo()
                if settings.SMTP_TLS:
                    server.starttls()
                    server.ehlo()

            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

            server.sendmail(settings.SMTP_FROM_EMAIL, [recipient_email], msg.as_string())
            logger.info("E-mail OTP envoyé avec succès à %s", recipient_email)
            return True
        except Exception as e:
            logger.error(
                "Échec de l'envoi SMTP pour %s (%s:%s, TLS=%s) : %s: %s",
                recipient_email, settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_TLS, type(e).__name__, e,
            )
            return False
        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    pass  # la connexion est déjà fermée

    def _render_otp_template(
        self,
        *,
        title: str,
        recipient_name: str,
        message_intro: str,
        code: str,
        validity_minutes: int,
    ) -> str:
        # Espacer visuellement les chiffres pour l'accessibilité
        formatted_code = " ".join(list(code))

        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f1f5f9; padding: 30px 15px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 540px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); overflow: hidden; border: 1px solid #e2e8f0;">
          <!-- En-tête -->
          <tr>
            <td style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 24px 30px; text-align: left;">
              <table role="presentation" width="100%">
                <tr>
                  <td>
                    <span style="display: inline-block; background-color: #4f46e5; color: #ffffff; font-weight: 800; font-size: 18px; padding: 6px 12px; border-radius: 6px; letter-spacing: 1px;">ENI</span>
                    <span style="color: #ffffff; font-size: 18px; font-weight: 600; margin-left: 10px; vertical-align: middle;">Mail</span>
                  </td>
                  <td align="right" style="color: #94a3b8; font-size: 12px;">
                    Sécurité des comptes
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Corps du message -->
          <tr>
            <td style="padding: 30px 30px 20px 30px;">
              <h1 style="font-size: 20px; font-weight: 700; color: #0f172a; margin-top: 0; margin-bottom: 12px;">{title}</h1>
              <p style="font-size: 14px; color: #475569; line-height: 1.6; margin-bottom: 20px;">
                Bonjour <strong>{recipient_name}</strong>,
              </p>
              <p style="font-size: 14px; color: #475569; line-height: 1.6; margin-bottom: 24px;">
                {message_intro}
              </p>

              <!-- Carte OTP -->
              <table role="presentation" width="100%" style="margin-bottom: 24px;">
                <tr>
                  <td align="center" style="background-color: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 10px; padding: 20px 10px;">
                    <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px; color: #64748b; margin-bottom: 8px;">Votre code à 6 chiffres</div>
                    <div style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #4f46e5;">
                      {formatted_code}
                    </div>
                    <div style="font-size: 12px; color: #dc2626; margin-top: 8px; font-weight: 500;">
                      ⏳ Valable pendant {validity_minutes} minutes
                    </div>
                  </td>
                </tr>
              </table>

              <!-- Avertissement de sécurité -->
              <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 12px 14px; border-radius: 4px; margin-bottom: 24px;">
                <p style="margin: 0; font-size: 12px; color: #991b1b; line-height: 1.5;">
                  <strong>Attention de sécurité :</strong> Ne transmettez ce code à personne. Aucun membre de l'équipe de l'ENI ne vous demandera votre code de vérification.
                </p>
              </div>

              <p style="font-size: 13px; color: #64748b; line-height: 1.5; margin-bottom: 0;">
                Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet e-mail en toute sécurité. Votre mot de passe actuel reste inchangé.
              </p>
            </td>
          </tr>

          <!-- Pied de page -->
          <tr>
            <td style="background-color: #f8fafc; padding: 16px 30px; border-top: 1px solid #e2e8f0; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #94a3b8;">
                École Nationale d'Informatique — ENI Fianarantsoa &bull; Plateforme de messagerie interne
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


email_service = EmailService()

