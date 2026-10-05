from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for every ORM model.

    All models subclass this so that `Base.metadata` is the single source of
    truth Alembic autogenerate compares against the live database.
    """
