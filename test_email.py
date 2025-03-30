from app import create_app
from app.models.user import User
from app.models.item import Item
from app.services.email_service import EmailService
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = create_app()
app.config['SERVER_NAME'] = 'localhost:5000'
app.config['PREFERRED_URL_SCHEME'] = 'http'
app.config['APPLICATION_ROOT'] = '/'

def test_email():
    with app.app_context():
        try:
            # Get the first user
            user = User.query.first()
            if not user:
                logger.error("No user found in the database")
                return
                
            logger.info(f"Found user: {user.username} ({user.email})")
            
            # Get actual items from inventory
            today = datetime.utcnow()
            items = Item.query.filter(
                Item.user_id == user.id,
                Item.expiry_date.isnot(None)
            ).all()
            
            logger.info(f"Found {len(items)} items in inventory")
            
            # Convert items to notification format, only including items that need attention
            notification_items = []
            for item in items:
                # Skip test items
                if item.name.lower().startswith('test'):
                    logger.info(f"Skipping test item: {item.name}")
                    continue
                    
                days_until_expiry = (item.expiry_date - today).days
                
                # Only include items expiring within 7 days
                if days_until_expiry > 7:
                    logger.info(f"Skipping item {item.name} as it expires in {days_until_expiry} days")
                    continue
                    
                if days_until_expiry <= 0:
                    priority = 'high'
                elif days_until_expiry <= 3:
                    priority = 'high'
                elif days_until_expiry <= 7:
                    priority = 'normal'
                else:
                    priority = 'low'
                    
                notification_items.append({
                    'name': item.name,
                    'days_until_expiry': days_until_expiry,
                    'priority': priority
                })
                logger.info(f"Item needing attention: {item.name}, Days until expiry: {days_until_expiry}, Priority: {priority}")
            
            # Send email with items needing attention
            if notification_items:
                logger.info(f"Attempting to send email to {user.email} with {len(notification_items)} items needing attention")
                success = EmailService.send_daily_notification_email(user, notification_items)
                if success:
                    logger.info(f"Email sent successfully to {user.email}")
                else:
                    logger.error("Failed to send email")
            else:
                logger.info("No items need attention at this time")
                
        except Exception as e:
            logger.error(f"Error in test_email: {str(e)}", exc_info=True)

if __name__ == '__main__':
    test_email() 