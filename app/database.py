from collections.abc import Generator
import os
from pathlib import Path
from urllib.parse import unquote

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./runtime/data/app.db")


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    database_path = database_url.removeprefix("sqlite:///")
    if database_path in {":memory:", ""}:
        return
    Path(unquote(database_path)).expanduser().parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(DATABASE_URL)


def enable_sqlite_foreign_keys(target_engine) -> None:
    """每个连接打开 SQLite 外键检查（F15 收尾）：引用不存在的父行时写入被拒。

    应用引擎必须调用；测试可对临时引擎调用同一函数以复现约束行为。
    """

    @event.listens_for(target_engine, "connect")
    def _set_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
enable_sqlite_foreign_keys(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
