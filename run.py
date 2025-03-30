import logging
from app import create_app
from app.core.extensions import db
from flask_migrate import upgrade
import os
from sqlalchemy import inspect

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

def init_db():
    """Initialize the database."""
    with app.app_context():
        try:
            logger.info("Checking database tables...")
            # Check if tables exist
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if not existing_tables:
                logger.info("No tables found. Creating database tables...")
                db.create_all()
                # Only run migrations if the migrations directory exists
                if os.path.exists('migrations'):
                    logger.info("Running database migrations...")
                    upgrade()
            else:
                logger.info(f"Found existing tables: {existing_tables}")
        except Exception as e:
            logger.error(f"Error during database initialization: {str(e)}")
            raise

if __name__ == '__main__':
    logger.info("Starting application...")
    init_db()
    logger.info("Starting Flask development server...")
    app.run(host='0.0.0.0', port=5000, debug=True) 