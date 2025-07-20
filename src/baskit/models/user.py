"""User model for BaskIt."""
from typing import Optional, List
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """Model representing a user."""
    
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Fields
    default_list_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("grocery_lists.id"),
        nullable=True
    )
    
    # Relationships
    lists = relationship(
        "GroceryList",
        back_populates="owner",
        foreign_keys="GroceryList.owner_id",
        cascade="all, delete-orphan"
    )
    
    default_list = relationship(
        "GroceryList",
        foreign_keys=[default_list_id]
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id})>" 