from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def sessions(url: str) -> sessionmaker[Session]:
    options = {}
    if url.startswith("sqlite"):
        options = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
    engine = create_engine(url, pool_pre_ping=True, **options)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):  # type: ignore[no-untyped-def]
            connection.execute("PRAGMA foreign_keys=ON")

    return sessionmaker(engine, expire_on_commit=False)
