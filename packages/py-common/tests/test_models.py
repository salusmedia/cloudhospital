import uuid

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from py_common.models import CommonColumns, uuid7


class _Base(DeclarativeBase):
    pass


class Sample(_Base, CommonColumns):
    __tablename__ = "sample"
    note: Mapped[str] = mapped_column(String(50), default="")


def test_uuid7_is_version_7():
    u = uuid7()
    assert isinstance(u, uuid.UUID)
    assert u.version == 7


def test_uuid7_is_time_ordered():
    a = uuid7()
    b = uuid7()
    # 同一毫秒可能并列，但绝不应倒序
    assert a.bytes[:6] <= b.bytes[:6]


def test_common_columns_present():
    cols = set(Sample.__table__.columns.keys())
    for c in (
        "id",
        "org_id",
        "dept_code",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "is_deleted",
        "row_version",
        "note",
    ):
        assert c in cols


def test_id_is_primary_key():
    assert Sample.__table__.c.id.primary_key
    assert Sample.__table__.c.dept_code.index
