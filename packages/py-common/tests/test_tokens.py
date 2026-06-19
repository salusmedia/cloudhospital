import time

import pytest

from py_common.tokens import TokenError, create_token, decode_token

SECRET = "test-secret"


def test_roundtrip():
    t = create_token({"sub": "u1", "name": "李医生", "roles": ["doctor"]}, SECRET)
    payload = decode_token(t, SECRET)
    assert payload["sub"] == "u1"
    assert payload["name"] == "李医生"
    assert payload["roles"] == ["doctor"]


def test_bad_signature():
    t = create_token({"sub": "u1"}, SECRET)
    with pytest.raises(TokenError):
        decode_token(t, "wrong-secret")


def test_tampered():
    t = create_token({"sub": "u1"}, SECRET)
    h, p, s = t.split(".")
    with pytest.raises(TokenError):
        decode_token(f"{h}.{p}x.{s}", SECRET)


def test_expired():
    t = create_token({"sub": "u1"}, SECRET, expires_in=-1)
    with pytest.raises(TokenError):
        decode_token(t, SECRET)


def test_malformed():
    with pytest.raises(TokenError):
        decode_token("not-a-token", SECRET)
