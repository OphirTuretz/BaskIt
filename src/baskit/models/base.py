"""Base SQLAlchemy models and mixins."""
from datetime import datetime, UTC
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.types import TypeDecorator


class TZDateTime(TypeDecorator):
    """Timezone-aware datetime type."""
    
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: Optional[datetime], dialect):
        """Convert datetime to UTC for storage."""
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            else:
                value = value.astimezone(UTC)
        return value

    def process_result_value(self, value: Optional[datetime], dialect):
        """Ensure retrieved datetime has UTC timezone."""
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class TimestampMixin:
    """Mixin that adds created/updated timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, 
        default=utc_now, 
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False
    )
    
    @declared_attr
    def created_by(cls) -> Mapped[Optional[int]]:
        return mapped_column(Integer, ForeignKey("users.id"))
    
    @declared_attr
    def updated_by(cls) -> Mapped[Optional[int]]:
        return mapped_column(Integer, ForeignKey("users.id"))


class SoftDeleteMixin:
    """Mixin that adds soft delete functionality."""
    
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TZDateTime
    )
    
    @declared_attr
    def deleted_by(cls) -> Mapped[Optional[int]]:
        return mapped_column(Integer, ForeignKey("users.id")) 