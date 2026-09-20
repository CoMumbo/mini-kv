import os
import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine, Integer, String, DateTime, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

from app.config import Config

log = logging.getLogger("mini-kv.db")


class Base(DeclarativeBase):
    pass


class BootRecord(Base):
    __tablename__ = "boots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class CommandCounter(Base):
    __tablename__ = "command_counter"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


# --- Engine setup -----------------------------------------------------------

def _make_engine():
    url = Config.DATABASE_URL
    if url.startswith("sqlite"):
        # Ensure the sqlite file's directory exists
        path = url.replace("sqlite:///", "")
        directory = os.path.dirname(path) or "."
        os.makedirs(directory, exist_ok=True)
    return create_engine(url, echo=False, future=True)


engine = _make_engine()


def init_db() -> None:
    """Create tables and record a boot event. Call once at startup."""
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(BootRecord())
        # Ensure the counter row exists
        existing = session.execute(select(CommandCounter).where(CommandCounter.id == 1)).scalar_one_or_none()
        if existing is None:
            session.add(CommandCounter(id=1, count=0))
        session.commit()
    log.info("metadata DB initialized")


def record_command(n: int = 1) -> None:
    """Increment the total command counter."""
    with Session(engine) as session:
        row = session.execute(select(CommandCounter).where(CommandCounter.id == 1)).scalar_one()
        row.count += n
        session.commit()


def get_stats() -> dict:
    """Return boot count and total commands processed."""
    with Session(engine) as session:
        boots = session.execute(select(func.count()).select_from(BootRecord)).scalar_one()
        counter = session.execute(select(CommandCounter).where(CommandCounter.id == 1)).scalar_one_or_none()
        commands = counter.count if counter else 0
    return {"boots": boots, "commands": commands}