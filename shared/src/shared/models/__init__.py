"""Domain ORM models.

Every model subclasses ``shared.db.base.Base`` so that importing this package
registers all tables on ``Base.metadata`` for Alembic autogenerate and for the
``import shared.models`` in db_migrations/env.py.
"""

from shared.models.outbox import OutboxEvent
from shared.models.payment import Payment


__all__ = ["OutboxEvent", "Payment"]
