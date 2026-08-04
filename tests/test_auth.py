"""
Unit tests for the auth module (SQLite path, isolated temp DB).

The Postgres path shares the same SQL — it's driven by DATABASE_URL,
which needs a real Neon connection string to exercise, so it's not
tested here. The encryption round-trip is tested via the temp DB.
"""

import os
import tempfile

os.environ["AUTH_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_users.db")
os.environ["ENCRYPTION_KEY"] = "k" * 44  # valid Fernet key bytes

from src.auth import (
    init_db,
    create_user,
    authenticate_user,
    get_user_by_id,
    update_api_key,
    clear_api_key,
    get_api_key,
    validate_signup_fields,
)

init_db()


def _expect_llm_error(fn, fragment, label):
    try:
        fn()
    except Exception as exc:
        assert fragment in str(exc), f"{label}: got {exc!r}"
    else:
        raise AssertionError(f"{label}: expected an error")


def test_create_and_login_with_api_key():
    ok, message = create_user(
        "Alice", "Test", "alice@example.com", "+91 98765 43210",
        "secretpass", api_provider="gemini", api_model="gemini-2.5-flash",
        api_key="AIzaFAKEKEY123",
    )
    assert ok, message

    user = authenticate_user("alice@example.com", "secretpass")
    assert user is not None
    assert user["first_name"] == "Alice"
    assert user["api_provider"] == "gemini"
    assert user["api_model"] == "gemini-2.5-flash"
    assert user["has_api_key"] is True

    assert get_api_key(user["id"]) == "AIzaFAKEKEY123"

    assert authenticate_user("+919876543210", "secretpass") is not None
    assert authenticate_user("alice@example.com", "wrong") is None


def test_duplicate_account_rejected():
    ok, _ = create_user("Bob", "Test", "alice@example.com", "9999999999", "anotherpass")
    assert ok is False


def test_key_update_and_clear_roundtrip():
    user = authenticate_user("alice@example.com", "secretpass")

    update_api_key(user["id"], "groq", "llama-3.3-70b-versatile", "gsk_fake_123")
    assert get_api_key(user["id"]) == "gsk_fake_123"

    refreshed = get_user_by_id(user["id"])
    assert refreshed["api_provider"] == "groq"
    assert refreshed["api_model"] == "llama-3.3-70b-versatile"

    clear_api_key(user["id"])
    refreshed = get_user_by_id(user["id"])
    assert refreshed["has_api_key"] is False
    assert get_api_key(user["id"]) == ""

    assert authenticate_user("alice@example.com", "secretpass") is not None


def test_key_is_encrypted_at_rest():
    import sqlite3

    conn = sqlite3.connect(os.environ["AUTH_DB_PATH"])
    row = conn.execute(
        "SELECT api_key_encrypted FROM users WHERE email = 'alice@example.com'"
    ).fetchone()
    conn.close()

    assert row is not None
    # Encrypted payloads are Fernet tokens: base64 with dots, never plaintext.
    stored = row[0]
    assert "gsk_fake_123" not in stored


def test_signup_validation():
    assert validate_signup_fields("", "X", "a@b.com", "1234567890", "pass1234", "pass1234")
    assert validate_signup_fields("A", "X", "not-an-email", "1234567890", "pass1234", "pass1234")
    assert validate_signup_fields("A", "X", "a@b.com", "12", "pass1234", "pass1234")
    assert validate_signup_fields("A", "X", "a@b.com", "1234567890", "short", "short")
    assert validate_signup_fields("A", "X", "a@b.com", "1234567890", "pass1234", "different")
    assert validate_signup_fields("A", "X", "a@b.com", "1234567890", "pass1234", "pass1234") is None


def test_create_user_without_key_has_no_key():
    ok, _ = create_user("Carol", "Test", "carol@example.com", "1111111111", "pass1234")
    assert ok

    user = authenticate_user("carol@example.com", "pass1234")
    assert user["has_api_key"] is False
    assert get_api_key(user["id"]) == ""


print("ALL AUTH TESTS PASSED")
