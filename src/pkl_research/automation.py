"""Automation Controller — semi/full mode + SMTP email + follow-up scheduler."""

from __future__ import annotations

import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from pkl_research import config
from pkl_research._compat import setup_utf8_io

setup_utf8_io()

MODES = ["semi", "full"]


def get_mode() -> str:
    mode = os.getenv("AUTOMATION_MODE", "semi").strip().lower()
    return mode if mode in MODES else "semi"


def is_full_auto() -> bool:
    return get_mode() == "full"


def _smtp_config() -> dict[str, object]:
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "pass": os.getenv("SMTP_PASS", ""),
    }


def send_email(
    to: str,
    subject: str,
    body: str,
    attachments: list[str | Path] | None = None,
) -> bool:
    """Kirim email via SMTP (Gmail app password). Return True jika sukses."""
    cfg = _smtp_config()
    if not cfg["user"] or not cfg["pass"]:
        raise RuntimeError(
            "SMTP_USER / SMTP_PASS belum diset di .env. "
            "Gmail: Settings > Security > App Password."
        )
    msg = MIMEMultipart()
    msg["From"] = str(cfg["user"])
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    for path in attachments or []:
        p = Path(path)
        if p.exists():
            with open(p, "rb") as f:
                part = MIMEApplication(f.read(), Name=p.name)
            part["Content-Disposition"] = f'attachment; filename="{p.name}"'
            msg.attach(part)

    try:
        with smtplib.SMTP(str(cfg["host"]), int(cfg["port"])) as server:
            server.starttls()
            server.login(str(cfg["user"]), str(cfg["pass"]))
            server.send_message(msg)
        return True
    except Exception:
        return False


def send_followup_wa(company_name: str, wa_number: str, applied_date: str, email_subject: str) -> str:
    """Generate follow-up WA message text (user kirim manual via wa.me link)."""
    return (
        f"Halo kak, saya Azka Syahirull dari SMK Cybermedia. "
        f"Saya sudah kirim lamaran PKL lewat email pada {applied_date} "
        f"dengan subjek '{email_subject}'. "
        f"Ini sekalian memastikan CV & sertifikat yang saya lampirkan sudah diterima. "
        f"Terima kasih!"
    )


class AutomationPipeline:
    """Pipeline otomatis: generate draft → kirim (jika full mode) → track."""

    def __init__(self, mode: str | None = None) -> None:
        self.mode = mode or get_mode()

    @property
    def is_full(self) -> bool:
        return self.mode == "full"

    def process_company(
        self,
        company_name: str,
        draft: str,
        contact_email: str,
        attachments: list[str | Path] | None = None,
        subject: str | None = None,
    ) -> dict[str, str]:
        """Proses satu perusahaan: draft + kirim (jika full) atau simpan (jika semi)."""
        if self.is_full and contact_email:
            sent = send_email(
                to=contact_email,
                subject=subject or f"Lamaran PKL - {company_name}",
                body=draft,
                attachments=attachments,
            )
            return {"action": "sent", "channel": "email", "success": sent}
        return {"action": "draft_saved", "channel": "manual", "success": True}
