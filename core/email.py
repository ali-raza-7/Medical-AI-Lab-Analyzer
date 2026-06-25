import os
import logging
import ssl
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")


FRONTEND_URL = os.getenv("FRONTEND_URL", "https://medical-ai-lab-analyzer.vercel.app")


def send_password_reset_email(to_email: str, token: str) -> bool:
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        logger.warning("[email] SMTP not configured — skipping password reset email to %s", to_email)
        return False

    link = f"{FRONTEND_URL}/reset-password?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Reset your password — Medical Lab Report Explainer"
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email
    msg.set_content(
        f"Hello,\n\nYou requested a password reset. Click the link below to set a new password:\n\n{link}\n\n"
        f"This link expires in 1 hour.\n\nIf you did not request this, please ignore this email."
    )
    msg.add_alternative(
        f"<h2>Password Reset</h2>"
        f"<p>You requested a password reset. Click the link below to set a new password:</p>"
        f"<p><a href=\"{link}\">{link}</a></p>"
        f"<p>This link expires in 1 hour.</p>"
        f"<p>If you did not request this, please ignore this email.</p>",
        subtype="html",
    )

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=ctx)
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("[email] Password reset email sent to %s", to_email)
        return True
    except Exception as exc:
        logger.error("[email] Failed to send password reset email to %s: %s", to_email, exc)
        return False


def send_verification_email(to_email: str, token: str) -> bool:
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        logger.warning(
            "[email] SMTP not configured — skipping verification email to %s", to_email
        )
        return False

    link = f"{BACKEND_PUBLIC_URL}/verify-email?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Verify your email — Medical Lab Report Explainer"
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email
    msg.set_content(
        f"Welcome!\n\nPlease verify your email by clicking the link below:\n\n{link}\n\n"
        f"This link expires in 24 hours.\n\n"
        f"If you did not create an account, please ignore this email."
    )
    msg.add_alternative(
        f"<h2>Welcome!</h2>"
        f"<p>Please verify your email by clicking the link below:</p>"
        f"<p><a href=\"{link}\">{link}</a></p>"
        f"<p>This link expires in 24 hours.</p>"
        f"<p>If you did not create an account, please ignore this email.</p>",
        subtype="html",
    )

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=ctx)
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("[email] Verification email sent to %s", to_email)
        return True
    except Exception as exc:
        logger.error(
            "[email] Failed to send verification email to %s: %s", to_email, exc
        )
        return False
