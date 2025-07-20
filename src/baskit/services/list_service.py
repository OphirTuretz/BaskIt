"""List management service."""
from typing import Optional, List, TypeVar, cast
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, update

from baskit.models import GroceryList, User
from baskit.domain.types import HebrewText
from .base_service import BaseService, Result


# Generic type for service results
T = TypeVar('T')


class ListService(BaseService):
    """Service for managing grocery lists."""

    def create_list(self, name: str) -> Result[GroceryList]:
        """
        Create a new grocery list.
        
        Args:
            name: Name of the list
            
        Returns:
            Result containing the created list or error
        """
        # Validate name
        self.logger.debug("Validating name", name=name)
        name_result = self._validate_name(name)
        if not name_result.success:
            self.logger.debug("Name validation failed", error=name_result.error)
            return cast(Result[GroceryList], name_result)
            
        try:
            # Validate Hebrew text
            self.logger.debug("Validating Hebrew text", name=name)
            try:
                hebrew_name = HebrewText(name)
                self.logger.debug("Hebrew text validation passed", name=hebrew_name)
            except (ValueError, TypeError) as e:
                self.logger.debug("Hebrew text validation failed", error=str(e))
                return Result.fail(str(e) if e.args else "שם לא תקין")
            
            with self.transaction.transaction() as session:
                # Check for existing list with same name
                existing = session.execute(
                    select(GroceryList)
                    .where(
                        GroceryList.name == hebrew_name,
                        GroceryList.owner_id == self.user_id,
                        GroceryList.is_deleted == False
                    )
                ).scalar_one_or_none()
                
                if existing:
                    self.logger.debug("Found existing list with same name", list_id=existing.id)
                    return self._handle_duplicate_error(hebrew_name)
                
                # Check for soft-deleted list with same name
                deleted = session.execute(
                    select(GroceryList)
                    .where(
                        GroceryList.name == hebrew_name,
                        GroceryList.owner_id == self.user_id,
                        GroceryList.is_deleted == True
                    )
                ).scalar_one_or_none()
                
                if deleted:
                    self.logger.debug("Found soft-deleted list with same name", list_id=deleted.id)
                    return Result.fail(
                        f"רשימה בשם '{hebrew_name}' נמחקה בעבר",
                        suggestions=[
                            "שחזר את הרשימה המחוקה",
                            "בחר שם אחר לרשימה החדשה"
                        ]
                    )
                
                # Create new list
                list_ = GroceryList(
                    name=hebrew_name,
                    owner_id=self.user_id,
                    created_by=self.user_id
                )
                session.add(list_)
                session.flush()  # Get ID before commit
                
                # Make default if user has no active lists
                active_lists = session.execute(
                    select(GroceryList)
                    .where(
                        GroceryList.owner_id == self.user_id,
                        GroceryList.is_deleted == False,
                        GroceryList.id != list_.id
                    )
                ).scalars().all()
                
                if not active_lists:
                    user = session.get(User, self.user_id)
                    if user:
                        user.default_list_id = list_.id
                
                session.commit()
                session.refresh(list_)  # Refresh to ensure all attributes loaded
                
                self._log_action("create_list", list_id=list_.id, name=hebrew_name)
                return Result.ok(list_)
                
        except IntegrityError:
            self.logger.debug("Integrity error while creating list", name=name)
            return self._handle_duplicate_error(name)
        except Exception as e:
            self.logger.exception("Failed to create list")
            return Result.fail("שגיאה ביצירת הרשימה")

    def delete_list(self, list_id: int, soft: bool = True) -> Result[GroceryList]:
        """
        Delete a grocery list.
        
        Args:
            list_id: ID of the list to delete
            soft: Whether to soft delete (default: True)
            
        Returns:
            Result indicating success or failure
        """
        try:
            with self.transaction.transaction() as session:
                list_ = session.get(GroceryList, list_id)
                if not list_:
                    return Result.fail("רשימה לא נמצאה")
                
                if list_.owner_id != self.user_id:
                    return Result.fail("אין הרשאה למחוק רשימה זו")
                
                if soft:
                    # Soft delete
                    list_.is_deleted = True
                    list_.deleted_at = self._get_now()
                    list_.deleted_by = self.user_id
                    
                    # Update default list if needed
                    user = session.get(User, self.user_id)
                    if user and user.default_list_id == list_id:
                        # Find first non-deleted list
                        new_default = session.execute(
                            select(GroceryList)
                            .where(
                                GroceryList.owner_id == self.user_id,
                                GroceryList.is_deleted == False,
                                GroceryList.id != list_id
                            )
                            .limit(1)
                        ).scalar_one_or_none()
                        
                        user.default_list_id = new_default.id if new_default else None
                else:
                    # Hard delete
                    session.delete(list_)
                
                session.commit()
                if soft:
                    session.refresh(list_)
                
                self._log_action(
                    "delete_list",
                    list_id=list_id,
                    soft=soft
                )
                return Result.ok(list_)
                
        except Exception as e:
            self.logger.exception("Failed to delete list")
            return Result.fail("שגיאה במחיקת הרשימה")

    def restore_list(self, list_id: int) -> Result[GroceryList]:
        """
        Restore a soft-deleted list.
        
        Args:
            list_id: ID of the list to restore
            
        Returns:
            Result containing the restored list or error
        """
        try:
            with self.transaction.transaction() as session:
                list_ = session.get(GroceryList, list_id)
                if not list_:
                    return Result.fail("רשימה לא נמצאה")
                
                if list_.owner_id != self.user_id:
                    return Result.fail("אין הרשאה לשחזר רשימה זו")
                
                if not list_.is_deleted:
                    return Result.fail("רשימה זו לא מחוקה")
                
                # Check for active list with same name
                existing = session.execute(
                    select(GroceryList)
                    .where(
                        GroceryList.name == list_.name,
                        GroceryList.owner_id == self.user_id,
                        GroceryList.is_deleted == False
                    )
                ).scalar_one_or_none()
                
                if existing:
                    return Result.fail(
                        f"קיימת רשימה פעילה בשם '{list_.name}'",
                        suggestions=[
                            "שנה את שם הרשימה לפני השחזור",
                            "מחק את הרשימה הפעילה תחילה"
                        ]
                    )
                
                # Restore list
                list_.is_deleted = False
                list_.deleted_at = None
                list_.deleted_by = None
                
                # Make default if no active lists
                active_lists = session.execute(
                    select(GroceryList)
                    .where(
                        GroceryList.owner_id == self.user_id,
                        GroceryList.is_deleted == False,
                        GroceryList.id != list_id
                    )
                ).scalars().all()
                
                if not active_lists:
                    user = session.get(User, self.user_id)
                    if user:
                        user.default_list_id = list_.id
                
                session.commit()
                session.refresh(list_)
                
                self._log_action("restore_list", list_id=list_id)
                return Result.ok(list_)
                
        except Exception as e:
            self.logger.exception("Failed to restore list")
            return Result.fail("שגיאה בשחזור הרשימה")

    def rename_list(self, list_id: int, new_name: str) -> Result[GroceryList]:
        """
        Rename a grocery list.
        
        Args:
            list_id: ID of the list to rename
            new_name: New name for the list
            
        Returns:
            Result containing the renamed list or error
        """
        # Validate name
        name_result = self._validate_name(new_name)
        if not name_result.success:
            return cast(Result[GroceryList], name_result)
            
        try:
            # Validate Hebrew text
            self.logger.debug("Validating Hebrew text", name=new_name)
            try:
                hebrew_name = HebrewText(new_name)
                self.logger.debug("Hebrew text validation passed", name=hebrew_name)
            except (ValueError, TypeError) as e:
                self.logger.debug("Hebrew text validation failed", error=str(e))
                return Result.fail(str(e) if e.args else "שם לא תקין")
            
            with self.transaction.transaction() as session:
                list_ = session.get(GroceryList, list_id)
                if not list_:
                    return Result.fail("רשימה לא נמצאה")
                
                if list_.owner_id != self.user_id:
                    return Result.fail("אין הרשאה לשנות רשימה זו")
                
                if list_.is_deleted:
                    return Result.fail("לא ניתן לשנות רשימה מחוקה")
                
                # Check for existing list with same name
                existing = session.execute(
                    select(GroceryList)
                    .where(
                        GroceryList.name == hebrew_name,
                        GroceryList.owner_id == self.user_id,
                        GroceryList.is_deleted == False,
                        GroceryList.id != list_id
                    )
                ).scalar_one_or_none()
                
                if existing:
                    return self._handle_duplicate_error(hebrew_name)
                
                # Update name
                list_.name = hebrew_name
                list_.updated_by = self.user_id
                
                session.commit()
                session.refresh(list_)
                
                self._log_action(
                    "rename_list",
                    list_id=list_id,
                    old_name=list_.name,
                    new_name=hebrew_name
                )
                return Result.ok(list_)
                
        except IntegrityError:
            self.logger.debug("Integrity error while renaming list", name=new_name)
            return self._handle_duplicate_error(hebrew_name)
        except Exception as e:
            self.logger.exception("Failed to rename list")
            return Result.fail("שגיאה בשינוי שם הרשימה")

    def set_default_list(self, list_id: int) -> Result[GroceryList]:
        """
        Set a list as the default list.
        
        Args:
            list_id: ID of the list to set as default
            
        Returns:
            Result containing the list or error
        """
        try:
            with self.transaction.transaction() as session:
                list_ = session.get(GroceryList, list_id)
                if not list_:
                    return Result.fail("רשימה לא נמצאה")
                
                if list_.owner_id != self.user_id:
                    return Result.fail("אין הרשאה לשנות רשימה זו")
                
                if list_.is_deleted:
                    return Result.fail("לא ניתן להגדיר רשימה מחוקה כברירת מחדל")
                
                # Update user's default list
                user = session.get(User, self.user_id)
                if user:
                    user.default_list_id = list_id
                
                session.commit()
                session.refresh(list_)
                
                self._log_action("set_default_list", list_id=list_id)
                return Result.ok(list_)
                
        except Exception as e:
            self.logger.exception("Failed to set default list")
            return Result.fail("שגיאה בהגדרת רשימת ברירת מחדל")

    def get_default_list(self) -> Result[Optional[GroceryList]]:
        """
        Get the user's default list.
        
        Returns:
            Result containing the default list or None if no default list
        """
        try:
            with self.transaction.transaction() as session:
                user = session.get(User, self.user_id)
                if not user or not user.default_list_id:
                    return Result.ok(None)
                
                list_ = session.get(GroceryList, user.default_list_id)
                if not list_ or list_.is_deleted:
                    if user:
                        user.default_list_id = None
                        session.commit()
                    return Result.ok(None)
                
                return Result.ok(list_)
                
        except Exception as e:
            self.logger.exception("Failed to get default list")
            return Result.fail("שגיאה בקבלת רשימת ברירת מחדל")

    def get_lists(self, include_deleted: bool = False) -> Result[List[GroceryList]]:
        """
        Get all lists owned by the user.
        
        Args:
            include_deleted: Whether to include soft-deleted lists
            
        Returns:
            Result containing list of grocery lists
        """
        try:
            with self.transaction.transaction() as session:
                query = select(GroceryList).where(GroceryList.owner_id == self.user_id)
                if not include_deleted:
                    query = query.where(GroceryList.is_deleted == False)
                
                lists = session.execute(query).scalars().all()
                return Result.ok(lists)
                
        except Exception as e:
            self.logger.exception("Failed to get lists")
            return Result.fail("שגיאה בקבלת רשימות") 