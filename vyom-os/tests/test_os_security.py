import pytest

from vyom_os.security import (
    Authorizer,
    InvalidToken,
    SignInThrottle,
    hash_password,
    issue_token,
    verify_password,
    verify_password_or_dummy,
    verify_token,
)

SECRET = b"s" * 48


def test_password_hash_round_trip():
    encoded = hash_password("correct horse battery")
    assert encoded.startswith("scrypt$")
    assert verify_password("correct horse battery", encoded)
    assert not verify_password("wrong horse battery", encoded)
    assert not verify_password_or_dummy("anything at all", None)


def test_token_round_trip_and_tamper():
    token, claims = issue_token(
        user_id="u1", email="a@demo-pharma.example", role="reviewer", tenant_id="t1",
        tenant_slug="demo-pharma", secret=SECRET, ttl_seconds=60, now=1_000,
    )
    assert verify_token(token, secret=SECRET, now=1_030) == claims
    with pytest.raises(InvalidToken):
        verify_token(token, secret=SECRET, now=1_061)
    with pytest.raises(InvalidToken):
        verify_token(token, secret=b"x" * 48, now=1_030)
    header, payload, signature = token.split(".")
    with pytest.raises(InvalidToken):
        verify_token(f"{header}.{payload[:-2]}AA.{signature}", secret=SECRET, now=1_030)


def test_unknown_role_cannot_get_a_token():
    with pytest.raises(ValueError):
        issue_token(user_id="u", email="e", role="superuser", tenant_id="t", tenant_slug="s", secret=SECRET, ttl_seconds=60)


def test_deny_wins_over_allow():
    authorizer = Authorizer([
        ("reviewer", "case.approve", "allow"),
        ("reviewer", "case.approve", "deny"),
        ("reviewer", "case.read", "allow"),
    ])
    assert not authorizer.allowed("reviewer", "case.approve")
    assert authorizer.allowed("reviewer", "case.read")
    assert not authorizer.allowed("qppv", "case.read")
    assert authorizer.permissions("reviewer") == ["case.read"]


def test_sign_in_throttle_locks_after_five_failures():
    throttle = SignInThrottle(limit=5, window_seconds=900)
    for second in range(5):
        throttle.failed("a@demo-pharma.example", now=float(second))
    assert throttle.blocked("a@demo-pharma.example", now=10.0)
    assert not throttle.blocked("a@demo-pharma.example", now=1000.0)
