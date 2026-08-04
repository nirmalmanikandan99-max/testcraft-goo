"""
User authentication — SQLite (local) or Neon Postgres (cloud).

Passwords are never stored in plain text: each user gets a random salt,
and PBKDF2-HMAC-SHA256 (stdlib `hashlib`, no extra dependency) derives
the stored hash.

Per-user AI API keys are stored encrypted (Fernet). The master key comes
from the ENCRYPTION_KEY environment variable / Streamlit secret; locally
a git-ignored `.encryption_key` file is created on first use.

Database selection:
  - DATABASE_URL env var set (Neon `postgresql://...`) -> Postgres
  - otherwise -> local SQLite file (AUTH_DB_PATH overrides the default
    name, used by tests to avoid touching the real users.db)
"""

import os
import re
import sqlite3
import hashlib
import secrets
from pathlib import Path
from datetime import datetime

DB_PATH = Path(os.environ.get("AUTH_DB_PATH", "users.db"))
DATABASE_URL = os.environ.get("DATABASE_URL", "")

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\+?\d{7,15}$")

PBKDF2_ITERATIONS = 200_000


def _is_postgres():
    return DATABASE_URL.startswith("postgres")


def _placeholder():
    """SQLite uses ? placeholders, Postgres uses %s."""
    return "%s" if _is_postgres() else "?"


def _get_connection():
    if _is_postgres():
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


_CREATE_TABLE_SQLITE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL,
    api_provider TEXT DEFAULT 'gemini',
    api_model TEXT DEFAULT '',
    api_key_encrypted TEXT DEFAULT ''
)
"""

_CREATE_TABLE_POSTGRES = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL,
    api_provider TEXT DEFAULT 'gemini',
    api_model TEXT DEFAULT '',
    api_key_encrypted TEXT DEFAULT ''
)
"""


def init_db():
    """Create/upgrade the users table on whichever DB is active."""

    with _get_connection() as conn:
        conn.execute(_CREATE_TABLE_POSTGRES if _is_postgres() else _CREATE_TABLE_SQLITE)

        # Migrate older DBs that predate the API-key columns.
        for column in (
            "api_provider TEXT DEFAULT 'gemini'",
            "api_model TEXT DEFAULT ''",
            "api_key_encrypted TEXT DEFAULT ''",
        ):
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {column}")
            except Exception:
                pass


# ------------------------------------------------------------------
# API-key encryption (Fernet)
# ------------------------------------------------------------------

def _load_master_key():
    """ENCRYPTION_KEY secret > local .encryption_key file (dev only)."""

    env_key = os.environ.get("ENCRYPTION_KEY", "").strip()
    if env_key:
        return env_key.encode()

    key_file = Path(".encryption_key")

    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip().encode()

    from cryptography.fernet import Fernet

    generated = Fernet.generate_key()
    key_file.write_text(generated.decode(), encoding="utf-8")
    return generated


def _fernet():
    from cryptography.fernet import Fernet
    return Fernet(_load_master_key())


def _encrypt_api_key(api_key):
    if not api_key:
        return ""
    try:
        return _fernet().encrypt(api_key.encode()).decode()
    except Exception:
        return api_key


def _decrypt_api_key(encrypted):
    if not encrypted:
        return ""
    try:
        return _fernet().decrypt(encrypted.encode()).decode()
    except Exception:
        return encrypted


# ------------------------------------------------------------------
# Password helpers
# ------------------------------------------------------------------

def _hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS
    )

    return derived.hex(), salt


def _normalize_phone(phone):
    return re.sub(r"[\s\-()]", "", phone)


# ------------------------------------------------------------------
# Account management
# ------------------------------------------------------------------

def validate_signup_fields(first_name, last_name, email, phone, password, confirm_password):
    """Return an error message string, or None if all fields are valid."""

    if not first_name.strip():
        return "First name is required."

    if not last_name.strip():
        return "Last name is required."

    if not EMAIL_PATTERN.match(email.strip()):
        return "Please enter a valid email address."

    if not PHONE_PATTERN.match(_normalize_phone(phone)):
        return "Please enter a valid phone number (7-15 digits)."

    if len(password) < 8:
        return "Password must be at least 8 characters long."

    if password != confirm_password:
        return "Passwords do not match."

    return None


def create_user(first_name, last_name, email, phone, password, api_provider="gemini", api_model="", api_key=""):
    """
    Create a new user account (optionally with their AI API key).

    Returns (success: bool, message: str).
    """

    email = email.strip().lower()
    phone = _normalize_phone(phone)
    api_key_encrypted = _encrypt_api_key(api_key.strip())

    with _get_connection() as conn:
        ph = _placeholder()

        existing = conn.execute(
            f"SELECT id FROM users WHERE email = {ph} OR phone = {ph}",
            (email, phone)
        ).fetchone()

        if existing:
            return False, "An account with this email or phone number already exists."

        password_hash, salt = _hash_password(password)

        conn.execute(
            f"""
            INSERT INTO users
                (first_name, last_name, email, phone, password_hash, salt, created_at,
                 api_provider, api_model, api_key_encrypted)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (
                first_name.strip(),
                last_name.strip(),
                email,
                phone,
                password_hash,
                salt,
                datetime.utcnow().isoformat(),
                api_provider.strip() or "gemini",
                api_model.strip(),
                api_key_encrypted,
            )
        )

    return True, "Account created successfully."


def authenticate_user(identifier, password):
    """
    Verify credentials against email or phone number.

    Returns the user dict on success, or None if authentication fails.
    """

    identifier = identifier.strip().lower()
    normalized_phone = _normalize_phone(identifier)

    with _get_connection() as conn:
        ph = _placeholder()

        row = conn.execute(
            f"SELECT * FROM users WHERE email = {ph} OR phone = {ph}",
            (identifier, normalized_phone)
        ).fetchone()

    if row is None:
        return None

    expected_hash, _ = _hash_password(password, salt=row["salt"])

    if not secrets.compare_digest(expected_hash, row["password_hash"]):
        return None

    return {
        "id": row["id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "email": row["email"],
        "phone": row["phone"],
        "api_provider": row["api_provider"] or "gemini",
        "api_model": row["api_model"] or "",
        "has_api_key": bool(row["api_key_encrypted"]),
    }


def get_user_by_id(user_id):
    """Fresh copy of a user's public info (used after key changes)."""

    with _get_connection() as conn:
        ph = _placeholder()

        row = conn.execute(
            f"SELECT * FROM users WHERE id = {ph}",
            (user_id,)
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "email": row["email"],
        "phone": row["phone"],
        "api_provider": row["api_provider"] or "gemini",
        "api_model": row["api_model"] or "",
        "has_api_key": bool(row["api_key_encrypted"]),
    }


def update_api_key(user_id, provider, model, api_key):
    """Save (or replace) the user's AI provider key."""

    with _get_connection() as conn:
        ph = _placeholder()

        conn.execute(
            f"UPDATE users SET api_provider = {ph}, api_model = {ph}, api_key_encrypted = {ph} WHERE id = {ph}",
            (provider.strip() or "gemini", model.strip(), _encrypt_api_key(api_key.strip()), user_id)
        )


def clear_api_key(user_id):
    """Remove the user's saved API key."""

    with _get_connection() as conn:
        ph = _placeholder()

        conn.execute(
            f"UPDATE users SET api_key_encrypted = '' WHERE id = {ph}",
            (user_id,)
        )


def get_api_key(user_id):
    """Decrypted API key for a user ('' if none saved)."""

    with _get_connection() as conn:
        ph = _placeholder()

        row = conn.execute(
            f"SELECT api_key_encrypted FROM users WHERE id = {ph}",
            (user_id,)
        ).fetchone()

    if row is None:
        return ""

    return _decrypt_api_key(row["api_key_encrypted"] or "")
