"""GroceryList model for BaskIt."""
from typing import Optional, List
from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, SoftDeleteMixin


class GroceryList(Base, TimestampMixin, SoftDeleteMixin):
    """Model representing a grocery list."""
    
    __tablename__ = "grocery_lists"
    
    # Ensure list names are unique per user
    __table_args__ = (
        UniqueConstraint(
            'name',
            'owner_id',
            'is_deleted',
            name='uq_list_name_owner_active'
        ),
    )
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Fields
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )
    
    # Relationships
    owner = relationship(
        "User",
        back_populates="lists",
        foreign_keys=[owner_id]
    )
    
    items = relationship(
        "GroceryItem",
        back_populates="list",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<GroceryList(id={self.id}, name='{self.name}')>" 