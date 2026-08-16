from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.privileged_access_log import PrivilegedAccessLog
from shared.security.privileged_access import make_privileged_access_sink

# Dedicated sync engine — the app's primary engine is async (asyncpg), but
# this hook runs synchronously inside get_validated_user. Same psycopg2 URL
# Alembic already uses for this database.
_engine = create_engine(settings.ai_database_url)
_SessionLocal = sessionmaker(bind=_engine)

write_privileged_access_log = make_privileged_access_sink(_SessionLocal, PrivilegedAccessLog)
