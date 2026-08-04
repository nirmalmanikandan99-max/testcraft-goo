"""
User authentication — SQLite-backed signup & login.

Passwords are never stored in plain text: each user gets a random salt,
and PBKDF2-HMAC-SHA256 (stdlib `hashlib`, no extra dependency) derives
the stored hash.
"""

import re
import sqlite3
import hashlib
import secrets
from pathlib import Path
from datetime import datetime

DB_PATH = Path("users.db")

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\+?\d{7,15}$")

PBKDF2_ITERATIONS = 200_000


def _get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    """Create the users table if it doesn't already exist."""

    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


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


def create_user(first_name, last_name, email, phone, password):
    """
    Create a new user account.

    Returns (success: bool, message: str).
    """

    email = email.strip().lower()
    phone = _normalize_phone(phone)

    with _get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ? OR phone = ?",
            (email, phone)
        ).fetchone()

        if existing:
            return False, "An account with this email or phone number already exists."

        password_hash, salt = _hash_password(password)

        conn.execute(
            """
            INSERT INTO users (first_name, last_name, email, phone, password_hash, salt, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                first_name.strip(),
                last_name.strip(),
                email,
                phone,
                password_hash,
                salt,
                datetime.utcnow().isoformat()
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
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            "SELECT * FROM users WHERE email = ? OR phone = ?",
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
    }
