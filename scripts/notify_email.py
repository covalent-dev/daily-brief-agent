#!/usr/bin/env python3
import socket
import subprocess
from datetime import datetime
from pathlib import Path
import smtplib
from email.message import EmailMessage
import yaml


def read_keychain(service: str) -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-w"],
        check=True,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def latest_brief_path(output_dir: Path, date_str: str) -> Path:
    md = output_dir / f"brief_{date_str}.md"
    return md if md.exists() else Path()


def find_daily_note(date_str: str) -> Path:
    vault = Path("/Users/taxman/Taxman_Progression_v4")
    daily_root = vault / "03_Documentation" / "Daily" / "2026"
    filename = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m-%d") + ".md"
    matches = list(daily_root.glob(f"Week-*/{filename}"))
    return matches[0] if matches else Path()


def load_vault_path() -> Path:
    config_path = Path("/Users/taxman/covalent-dev/daily-brief-agent/config/feeds.yaml")
    try:
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception:
        return Path()
    vault_cfg = cfg.get("settings", {}).get("vault_sync", {})
    if vault_cfg.get("enabled") and vault_cfg.get("vault_path"):
        return Path(vault_cfg["vault_path"])
    return Path()


def main() -> None:
    try:
        gmail_user = read_keychain("daily-brief-gmail-user")
        gmail_pass = read_keychain("daily-brief-gmail-pass")
        to_addr = read_keychain("daily-brief-email-to")
    except subprocess.CalledProcessError:
        print("Missing keychain items. Expected services: daily-brief-gmail-user, daily-brief-gmail-pass, daily-brief-email-to")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path("/Users/taxman/covalent-dev/daily-brief-agent/output")
    brief_path = latest_brief_path(output_dir, today)
    daily_note_path = find_daily_note(today)
    vault_path = load_vault_path()
    vault_brief = Path()
    if vault_path:
        candidate = vault_path / f"brief_{today}.md"
        if candidate.exists():
            vault_brief = candidate

    subject = f"Daily Brief Run - {today}"
    lines = [
        f"Date: {today}",
        "",
        "Status:",
        f"- Daily note: {'OK' if daily_note_path else 'MISSING'}",
        f"- Brief file (project output): {'OK' if brief_path else 'MISSING'}",
        f"- Brief file (vault sync): {'OK' if vault_brief else 'MISSING' if vault_path else 'NOT CONFIGURED'}",
    ]
    if brief_path:
        lines.append(f"- Brief path: {brief_path}")
    if daily_note_path:
        lines.append(f"- Daily note path: {daily_note_path}")
    if vault_brief:
        lines.append(f"- Vault brief path: {vault_brief}")
    lines.append("")
    lines.append("If brief is missing, check logs:")
    lines.append(str(output_dir / "launchd.log"))

    msg = EmailMessage()
    msg["From"] = gmail_user
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content("\n".join(lines))

    try:
        socket.getaddrinfo("smtp.gmail.com", 587)
    except OSError:
        print("Network/DNS unavailable; skipping email notification")
        return

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(gmail_user, gmail_pass)
        smtp.send_message(msg)


if __name__ == "__main__":
    main()
