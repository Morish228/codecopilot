import uuid

from coding_assistant.control_plane.auth import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("secret-password")
    assert verify_password("secret-password", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_encode_decode(monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET",
        "test-secret-key-at-least-32-bytes-long!!",
    )
    from coding_assistant.config import get_settings

    get_settings.cache_clear()

    uid = uuid.uuid4()
    token = create_access_token(user_id=uid, org_id=None, role="owner")
    payload = decode_access_token(token)
    assert payload["sub"] == str(uid)

    get_settings.cache_clear()
