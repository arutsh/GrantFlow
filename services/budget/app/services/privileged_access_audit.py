from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.privileged_access_log import PrivilegedAccessLog
from shared.security.privileged_access import make_privileged_access_sink

# Dedicated sync engine: this hook runs synchronously, unlike the app's async primary engine.
_engine = create_engine(settings.budget_database_url)
_SessionLocal = sessionmaker(bind=_engine)

write_privileged_access_log = make_privileged_access_sink(_SessionLocal, PrivilegedAccessLog)
