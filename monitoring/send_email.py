#!/usr/bin/env python3
import os
import sys
import smtplib
from email.message import EmailMessage
from pathlib import Path
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None


def send_email(to_addr: str, subject: str, body: str, attachments: list[str] | None = None) -> None:
    # Load .env from the monitoring directory if available
    if load_dotenv is not None:
        env_path = Path(__file__).resolve().parent / ".env"
        try:
            if env_path.exists():
                load_dotenv(dotenv_path=str(env_path), override=False)
        except Exception:
            pass

    host = os.getenv("SMTP_HOST", "localhost")
    port = int(os.getenv("SMTP_PORT", "25"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    use_ssl = os.getenv("SMTP_SSL", "false").lower() == "true"
    from_addr = os.getenv("MAIL_FROM", user or f"noreply@{os.uname().nodename}")

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    for att in attachments or []:
        p = Path(att)
        if not p.exists():
            continue
        data = p.read_bytes()
        # Best-effort content type
        maintype = "application"
        subtype = "octet-stream"
        if p.suffix.lower() in (".png", ".jpg", ".jpeg"):
            maintype = "image"; subtype = p.suffix.lower().lstrip(".")
        elif p.suffix.lower() in (".html", ".htm"):
            maintype = "text"; subtype = "html"
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=p.name)

    if use_ssl:
        with smtplib.SMTP_SSL(host, port) as s:
            if user and password:
                s.login(user, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as s:
            if user and password:
                s.starttls()
                s.login(user, password)
            s.send_message(msg)


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Send email with optional attachments via SMTP (env-configurable)")
    ap.add_argument("--to", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body", required=True)
    ap.add_argument("--attach", action="append", default=[])
    args = ap.parse_args(argv)
    send_email(args.to, args.subject, args.body, args.attach)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
