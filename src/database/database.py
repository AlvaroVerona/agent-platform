import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# =====================================================
# DATABASE URL
# =====================================================

# NOTA: el DATABASE_URL del .env apunta a un Postgres con un esquema "runs"
# antiguo e incompatible. Hasta migrar ese esquema, forzamos SQLite aquí.
load_dotenv()

# Ruta absoluta (no relativa al cwd: un cliente MCP lanza el proceso desde cualquier sitio).
# AGENT_PLATFORM_DB permite elegir otro fichero SQLite.
_DEFAULT_DB = Path(__file__).resolve().parents[2] / "agent_platform.db"
DATABASE_URL = f"sqlite:///{os.environ.get('AGENT_PLATFORM_DB', _DEFAULT_DB)}"

# =====================================================
# SQLALCHEMY ENGINE
# =====================================================

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

# =====================================================
# SESSION FACTORY
# =====================================================

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

# =====================================================
# BASE MODEL
# =====================================================

Base = declarative_base()


# =====================================================
# DEPENDENCY (FastAPI READY)
# =====================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()