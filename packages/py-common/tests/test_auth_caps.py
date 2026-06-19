import pytest
from fastapi import HTTPException

from py_common.auth import AuthUser, get_current_user, require_cap


def test_has_cap():
    u = AuthUser(user_id="u1", name="王医生", caps=["teleclinic:prescribe"])
    assert u.has_cap("teleclinic:prescribe")
    assert not u.has_cap("referral:receive")


def test_get_current_user_parses_caps():
    u = get_current_user(
        x_user_id="u1",
        x_user_name="%E7%8E%8B%E5%8C%BB%E7%94%9F",  # URL-encode 的中文名
        x_user_roles="doctor",
        x_user_scopes="card",
        x_user_caps="teleclinic:prescribe,referral:receive",
    )
    assert u.name == "王医生"
    assert u.caps == ["teleclinic:prescribe", "referral:receive"]


def test_require_cap_allows_when_present():
    u = AuthUser(user_id="u1", name="王医生", caps=["teleclinic:prescribe"])
    checker = require_cap("teleclinic:prescribe")
    assert checker(user=u) is u


def test_require_cap_denies_when_absent():
    u = AuthUser(user_id="u2", name="李医生", caps=["referral:initiate"])
    checker = require_cap("teleclinic:prescribe")
    with pytest.raises(HTTPException) as exc:
        checker(user=u)
    assert exc.value.status_code == 403
