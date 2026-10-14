from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from src.database.database import Base


def _utcnow():
    return datetime.now(UTC)


class Run(Base):
    """
    Una ejecución completa del pipeline Product -> Tech -> QA.

    Los ciclos Tech -> QA intermedios viven en `iterations`.
    """

    __tablename__ = "runs"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=_utcnow,
        nullable=False,
    )

    idea = Column(
        String,
        nullable=False,
    )

    status = Column(
        String,
        nullable=False,
        default="CREATED",
    )

    product_spec = Column(
        JSON,
        nullable=True,
    )

    # Solo se rellena cuando QA aprueba una iteración
    final_tech_spec = Column(
        JSON,
        nullable=True,
    )

    iterations = relationship(
        "Iteration",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="Iteration.index",
    )


class Iteration(Base):
    """
    Un ciclo Tech -> QA dentro de un run.
    """

    __tablename__ = "iterations"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    run_id = Column(
        Integer,
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    index = Column(
        Integer,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=_utcnow,
        nullable=False,
    )

    tech_spec = Column(
        JSON,
        nullable=True,
    )

    qa_report = Column(
        JSON,
        nullable=True,
    )

    approved = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    run = relationship(
        "Run",
        back_populates="iterations",
    )
