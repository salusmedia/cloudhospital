from app.identity import build_identity_headers, extract_bearer, strip_client_identity
from app.routing import Route, resolve_route, upstream_url

ROUTES = [
    Route("/api/scenario-001", "scenario-001-backend", 8001),
    Route("/api/platform-auth/login", "platform-auth", 8101, public=True),
    Route("/api/platform-auth", "platform-auth", 8101),
]
ROUTES.sort(key=lambda r: len(r.prefix), reverse=True)


def test_longest_prefix_wins():
    r = resolve_route("/api/platform-auth/login", ROUTES)
    assert r is not None and r.public is True
    r2 = resolve_route("/api/platform-auth/me", ROUTES)
    assert r2 is not None and r2.public is False


def test_boundary_no_false_match():
    # /api/scenario-0011 不应匹配 /api/scenario-001
    assert resolve_route("/api/scenario-0011/x", ROUTES) is None


def test_unknown_route():
    assert resolve_route("/api/nope", ROUTES) is None


def test_upstream_url():
    r = Route("/api/scenario-001", "scenario-001-backend", 8001)
    assert (
        upstream_url(r, "/api/scenario-001/followups", "on=2026-06-01", use_localhost=False)
        == "http://scenario-001-backend:8001/api/scenario-001/followups?on=2026-06-01"
    )
    assert upstream_url(r, "/api/scenario-001/ping", "", use_localhost=True).startswith(
        "http://localhost:8001"
    )


def test_strip_client_identity_blocks_spoofing():
    stripped = strip_client_identity(
        {"X-User-Id": "hacker", "Authorization": "Bearer x", "Accept": "application/json"}
    )
    assert "X-User-Id" not in stripped
    assert "Authorization" not in stripped
    assert stripped["Accept"] == "application/json"


def test_build_identity_headers_encodes_name():
    h = build_identity_headers(
        {
            "sub": "u1",
            "name": "李医生",
            "roles": ["doctor"],
            "scopes": ["card"],
            "caps": ["referral:receive"],
        }
    )
    assert h["X-User-Id"] == "u1"
    assert h["X-User-Name"] == "%E6%9D%8E%E5%8C%BB%E7%94%9F"  # URL-encoded
    assert h["X-User-Roles"] == "doctor"
    assert h["X-User-Scopes"] == "card"
    assert h["X-User-Caps"] == "referral:receive"


def test_extract_bearer():
    assert extract_bearer({"Authorization": "Bearer abc"}) == "abc"
    assert extract_bearer({"authorization": "bearer xyz"}) == "xyz"
    assert extract_bearer({"Authorization": "Basic abc"}) is None
    assert extract_bearer({}) is None
