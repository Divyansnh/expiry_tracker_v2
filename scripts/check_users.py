import logging
from app import create_app
from app.models.user import User
from app.core.extensions import db
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    app = create_app()
    
    with app.app_context():
        # Test database connection
        logger.info("Testing database connection...")
        db.session.execute(text("SELECT 1"))
        logger.info("Database connection successful!")
        
        # Count users
        total_users = User.query.count()
        print(f"\nTotal registered users: {total_users}")
        
        # Get details of each user
        users = User.query.all()
        print("\nUser Details:")
        for user in users:
            print(f"- Username: {user.username}, Email: {user.email}, Created: {user.created_at}")
            
except Exception as e:
    logger.error(f"Error occurred: {str(e)}", exc_info=True)
    print(f"Error: {str(e)}") 