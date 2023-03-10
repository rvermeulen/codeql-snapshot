from sqlalchemy.orm import (
    DeclarativeBase,
    MappedAsDataclass,
    Mapped,
    mapped_column,
    validates,
)
from sqlalchemy import event
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
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.utcnow()


class Base(MappedAsDataclass, DeclarativeBase, TimeStampMixin):
    pass
