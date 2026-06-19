"""本场景的数据库会话。统一用 py-common 的 DB 基类，不要各自造轮子。"""

from __future__ import annotations

from app.core.config import settings
from py_common.db import make_session_factory, session_dependency

SessionFactory = make_session_factory(settings.database_url)

# FastAPI 依赖：一次请求一个会话，正常结束自动 commit，异常自动 rollback。
get_db = session_dependency(SessionFactory)
