"""One-time setup for the Vercel demo with a shared Neon PostgreSQL database.

Run from the backend folder:   python -m scripts.vercel_setup

It asks for the Neon connection string and a demo password, then:
  1. creates the tables (alembic upgrade head),
  2. adds the demo teacher/student accounts and classes (app.seed),
  3. generates fresh signing keys,
  4. writes every Vercel environment variable to ../.env.vercel.local (git-ignored),
     ready to paste into Vercel > Settings > Environment Variables.

Demo only: never use real student data with the demo accounts.
"""
import getpass
import os
import secrets
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
OUT = ROOT / ".env.vercel.local"
POSTGRES_PREFIXES = ("postgres://", "postgresql://", "postgresql+psycopg://")


def ask_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip() or input("Paste the Neon connection string: ").strip()
    if url.startswith("psql "):  # Neon can also show the string as a psql command
        url = url[5:].strip()
    url = url.strip("'\"")
    if not url.startswith(POSTGRES_PREFIXES):
        sys.exit("That is not a PostgreSQL connection string. Copy the one that starts with postgresql:// from Neon.")
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


def ask_password() -> str:
    password = os.environ.get("DEV_PASSWORD", "")
    while len(password) < 12:
        password = getpass.getpass("Choose a demo password (at least 12 characters, it will not be shown): ")
        if len(password) < 12:
            print("Too short, try again.")
    return password


def run(step: str, command: list[str], env: dict[str, str]) -> None:
    print(f"\n==> {step}")
    result = subprocess.run(command, cwd=BACKEND, env=env)
    if result.returncode != 0:
        sys.exit(f"Step failed: {step}. Read the error above, fix it, and run this script again.")


def main() -> None:
    url = ask_database_url()
    password = ask_password()
    env = {k: v for k, v in os.environ.items() if k != "MOCK_DATA"}
    env.update(DATABASE_URL=url, APP_ENV="development", ENABLE_DEV_AUTH="true", DEV_PASSWORD=password, MOCK_DATA="false")

    run("Creating the database tables", [sys.executable, "-m", "alembic", "upgrade", "head"], env)
    run("Adding the demo accounts and classes", [sys.executable, "-m", "app.seed"], env)

    variables = {
        "DATABASE_URL": url,
        "APP_ENV": "development",
        "ENABLE_DEV_AUTH": "true",
        "DEV_PASSWORD": password,
        "QR_SIGNING_KEY": secrets.token_urlsafe(48),
        "POLICY_SIGNING_KEY": secrets.token_urlsafe(48),
        "BLE_TOKEN_KEY": secrets.token_urlsafe(48),
        "CRON_SECRET": secrets.token_urlsafe(32),
        "FACE_CHECK_MODE": "off",
        "PLAY_INTEGRITY_MODE": "off",
        "RESOURCE_ALLOWED_HOSTS": "college.example.edu,docs.college.example.edu",
    }
    OUT.write_text("".join(f"{k}={v}\n" for k, v in variables.items()), encoding="utf-8")
    try:
        OUT.chmod(0o600)
    except OSError:
        pass

    print(f"\nDone. The Vercel environment variables are in:\n  {OUT}")
    print("Open it, copy everything, and paste it into Vercel > Project > Settings > Environment Variables.")
    print("Keep this file private: it holds the database password and the signing keys. It is git-ignored.")


if __name__ == "__main__":
    main()
