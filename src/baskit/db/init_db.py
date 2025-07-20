"""Database initialization script."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from baskit.models import Base, User, GroceryList
from baskit.config.settings import get_settings

settings = get_settings()

def init_db():
    """Initialize the database with tables and test data."""
    # Create engine
    engine = create_engine(settings.DB_URL)
    
    # Create tables
    Base.metadata.create_all(engine)
    
    # Create test user and default list
    with Session(engine) as session:
        # Check if test user exists
        test_user = session.query(User).filter_by(id=1).first()
        if not test_user:
            test_user = User(id=1)
            session.add(test_user)
            
            # Create default list
            default_list = GroceryList(
                name=settings.DEFAULT_LIST_NAME,
                owner_id=test_user.id,
                created_by=test_user.id
            )
            session.add(default_list)
            
            # Set as default list
            test_user.default_list_id = default_list.id
            
            session.commit()
            print("Created test user and default list")
        else:
            print("Test user already exists")


if __name__ == "__main__":
    init_db() 