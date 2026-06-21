from app.core.config import settings
from py_common.db import make_session_factory, session_dependency

SessionFactory = make_session_factory(settings.database_url)
get_db = session_dependency(SessionFactory)
