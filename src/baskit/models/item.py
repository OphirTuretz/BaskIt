"""GroceryItem model for BaskIt."""
from typing import Optional
from datetime import datetime
from sqlalchemy import String, ForeignKey, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class GroceryItem(Base, TimestampMixin):
    """Model representing an item in a grocery list."""
    
    __tablename__ = "grocery_items"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Fields
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="יחידה", nullable=False)
    is_bought: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bought_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Foreign keys
    list_id: Mapped[int] = mapped_column(
        ForeignKey("grocery_lists.id"),
        nullable=False
    )
    
    # Relationships
    list = relationship(
        "GroceryList",
        back_populates="items"
    )
    
    def __repr__(self) -> str:
        return f"<GroceryItem(id={self.id}, name='{self.name}', quantity={self.quantity})>" 