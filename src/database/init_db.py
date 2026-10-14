from src.database.database import Base, engine
from src.database.models import Iteration, Run  # noqa: F401  (importing the models registers their tables on Base)


def init_db():
    Base.metadata.create_all(bind=engine)
