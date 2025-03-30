from datetime import datetime, timedelta
from app.core.extensions import db
from app.models.item import Item
from app.models.notification import Notification
from app.services.zoho_service import ZohoService
from flask import current_app

def cleanup_expired_items():
    """Cleanup expired items and send notifications."""
    try:
        current_date = datetime.now().date()
        yesterday = current_date - timedelta(days=1)
        
        # Find items that expired yesterday
        expired_items = Item.query.filter(
            Item.expiry_date == yesterday,
            Item.status == 'Expired'
        ).all()
        
        zoho_service = ZohoService()
        
        for item in expired_items:
            # Create notification for the user
            notification = Notification(
                user_id=item.user_id,
                message=f"Item '{item.name}' (ID: {item.id}) has expired and will be removed from the system."
            )
            db.session.add(notification)
            
            # Mark item as inactive in Zoho if it has a Zoho ID
            if item.zoho_item_id:
                zoho_service.delete_item_in_zoho(item.zoho_item_id)
            
            # Remove item from database
            db.session.delete(item)
        
        db.session.commit()
        current_app.logger.info(f"Successfully cleaned up {len(expired_items)} expired items")
        
    except Exception as e:
        current_app.logger.error(f"Error cleaning up expired items: {str(e)}")
        db.session.rollback() 