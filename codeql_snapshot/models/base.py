from sqlalchemy.orm import (
    DeclarativeBase,
    MappedAsDataclass,
    Mapped,
    mapped_column,
    validates
)
from sqlalchemy import event, MetaData
from datetime import datetime
from typing import Any


# Use a mixin to add the timestamp columns to all models, because an update event is not triggered for the Base class for unknown reasons.
class TimeStampMixin:
    created_at: Mapped[datetime] = mapped_column(init=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(init=False, default=datetime.utcnow)

    @validates("created_at", "updated_at")
    def ensure_write_once(self, key: str, value: Any) -> Any:
        existing = getattr(self, key)
        if existing:
            raise ValueError(f"The field {key} should not be updated!")
        return value


@event.listens_for(TimeStampMixin, "before_update", propagate=True)
def receive_before_update(mapper: Any, connection: Any, target: TimeStampMixin):
    target.updated_at = datetime.utcnow()


class Base(MappedAsDataclass, DeclarativeBase, TimeStampMixin):
    # Add explicit naming convention for deterministic database migrations.
    # https://alembic.sqlalchemy.org/en/latest/naming.html
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_`%(constraint_name)s`",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    })
