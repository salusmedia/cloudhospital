from sqlalchemy import String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from py_common.auth import AuthUser
from py_common.authz import has_global_scope, scope_filter
from py_common.models import CommonColumns


class _Base(DeclarativeBase):
    pass


class Rec(_Base, CommonColumns):
    __tablename__ = "rec"
    note: Mapped[str] = mapped_column(String(50), default="")


def _sql(stmt) -> str:
    """编译为带字面量的 SQL（便于断言 dept_code / 哨兵值）。"""
    return str(stmt.compile(compile_kwargs={"literal_binds": True})).lower()


def _sql_raw(stmt) -> str:
    """编译为带占位符的 SQL（用于含 UUID 列、无法字面量化的场景）。"""
    return str(stmt.compile()).lower()


def test_limited_scope_filters_by_dept_and_excludes_deleted():
    user = AuthUser(user_id="u1", name="李医生", roles=["doctor"], scopes=["card"])
    sql = _sql(scope_filter(select(Rec), Rec, user))
    assert "dept_code in" in sql
    assert "'card'" in sql
    assert "where" in sql
    assert "is_deleted is" in sql  # WHERE 里的软删除过滤（区别于 SELECT 列）


def test_global_scope_skips_dept_filter():
    admin = AuthUser(user_id="u0", name="管理员", roles=["admin"], scopes=["all"])
    assert has_global_scope(admin)
    sql = _sql(scope_filter(select(Rec), Rec, admin))
    assert "dept_code in" not in sql
    assert "is_deleted is" in sql  # 仍排除软删除


def test_no_scope_sees_nothing():
    user = AuthUser(user_id="u2", name="无权", roles=["doctor"], scopes=[])
    sql = _sql(scope_filter(select(Rec), Rec, user))
    assert "__none__" in sql


def test_record_grant_ids_are_or_ed_in():
    user = AuthUser(user_id="u1", name="李医生", roles=["doctor"], scopes=["card"])
    stmt = scope_filter(select(Rec), Rec, user, extra_visible_ids=["abc"])
    sql = _sql_raw(stmt)
    assert "dept_code in" in sql
    assert " or " in sql
    assert "rec.id in" in sql


def test_include_deleted_admin_has_no_where():
    admin = AuthUser(user_id="u0", name="管理员", roles=["admin"], scopes=["all"])
    sql = _sql(scope_filter(select(Rec), Rec, admin, include_deleted=True))
    assert "where" not in sql  # 全局 + 含软删除 → 不加任何过滤
