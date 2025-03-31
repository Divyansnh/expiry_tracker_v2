from datetime import datetime, timedelta
from typing import List, Optional, Union, Dict
from flask import current_app
from app.core.extensions import db
from app.models.notification import Notification
from app.models.item import Item
from app.models.user import User
from app.services.email_service import EmailService

class NotificationService:
    """Service for handling expiry notifications."""
    
    def __init__(self):
        self._notification_days = None
    
    @property
    def notification_days(self):
        """Get notification days from config."""
        if self._notification_days is None:
            self._notification_days = current_app.config['NOTIFICATION_DAYS']
        return self._notification_days
    
    def check_expiry_dates(self) -> List[Notification]:
        """Check items for expiry and create notifications."""
        notifications = []
        today = datetime.utcnow()
        
        # Group notifications by user
        user_notifications: Dict[int, Dict] = {}
        
        # Get all items with expiry dates
        items = Item.query.filter(
            Item.expiry_date.isnot(None),
            Item.expiry_date > today
        ).all()
        
        # Get recently expired items (expired in last 24 hours)
        recently_expired = Item.query.filter(
            Item.expiry_date.isnot(None),
            Item.expiry_date <= today,
            Item.expiry_date >= today - timedelta(days=1)
        ).all()
        
        # Handle recently expired items first
        for item in recently_expired:
            if item.user.email_notifications:
                if item.user_id not in user_notifications:
                    user_notifications[item.user_id] = {
                        'expiring': [],
                        'expired': []
                    }
                
                user_notifications[item.user_id]['expired'].append({
                    'name': item.name,
                    'days_until_expiry': 0,
                    'priority': 'high'
                })
        
        # Handle items approaching expiry
        for item in items:
            days_until_expiry = item.days_until_expiry
            
            # Check if we need to send a notification
            if days_until_expiry in self.notification_days:
                notification = self._create_notification(item)
                if notification:
                    notifications.append(notification)
                    
                    # Group notification by user
                    if item.user.email_notifications:
                        if item.user_id not in user_notifications:
                            user_notifications[item.user_id] = {
                                'expiring': [],
                                'expired': []
                            }
                        
                        user_notifications[item.user_id]['expiring'].append({
                            'name': item.name,
                            'days_until_expiry': days_until_expiry,
                            'priority': notification.priority
                        })
        
        # Send batched email notifications
        for user_id, data in user_notifications.items():
            user = User.query.get(user_id)
            if user and self._should_send_email(user_id):
                # Combine expiring and expired items
                all_items = data['expired'] + data['expiring']
                # Sort items by priority (high -> normal -> low)
                all_items.sort(key=lambda x: {'high': 0, 'normal': 1, 'low': 2}[x['priority']])
                
                if all_items:  # Only send if there are items to notify about
                    if EmailService.send_daily_notification_email(user, all_items):
                        self._mark_email_sent(user_id)
        
        return notifications
    
    def _should_send_email(self, user_id: int) -> bool:
        """Check if we should send an email to this user."""
        # Get the last email notification for this user
        last_notification = Notification.query.filter_by(
            user_id=user_id,
            type='email',
            status='sent'
        ).order_by(Notification.created_at.desc()).first()
        
        if not last_notification:
            return True
            
        # Check if 24 hours have passed since the last email
        hours_since_last = (datetime.utcnow() - last_notification.created_at).total_seconds() / 3600
        return hours_since_last >= 24
    
    def _mark_email_sent(self, user_id: int):
        """Mark that an email was sent to this user."""
        notification = Notification(
            message="Daily expiry alert email sent",
            type='email',
            status='sent',
            user_id=user_id
        )
        db.session.add(notification)
        db.session.commit()
    
    def _create_notification(self, item: Item) -> Optional[Notification]:
        """Create a notification for an item."""
        days_until_expiry = item.days_until_expiry
        
        # Determine priority based on days until expiry
        if days_until_expiry == 1:
            priority = 'high'
            message = f"Critical: Product {item.name} (ID: {item.id}) expires tomorrow!"
        elif days_until_expiry <= 3:
            priority = 'high'
            message = f"Warning: Product {item.name} (ID: {item.id}) expires in {days_until_expiry} days!"
        elif days_until_expiry <= 7:
            priority = 'normal'
            message = f"Notice: Product {item.name} (ID: {item.id}) expires in {days_until_expiry} days."
        else:
            priority = 'low'
            message = f"Info: Product {item.name} (ID: {item.id}) expires in {days_until_expiry} days."
        
        # Check if notification already exists for this specific day
        existing = Notification.query.filter_by(
            item_id=item.id,
            type='in_app',
            status='pending',
            message=message
        ).first()
        
        if existing:
            return None
        
        notification = Notification(
            message=message,
            type='in_app',
            priority=priority,
            user_id=item.user_id,
            item_id=item.id
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return notification
    
    def send_sms_notification(self, notification: Notification) -> bool:
        """Send SMS notification using Twilio."""
        if not current_app.config['TWILIO_ACCOUNT_SID']:
            return False
            
        try:
            from twilio.rest import Client
            
            client = Client(
                current_app.config['TWILIO_ACCOUNT_SID'],
                current_app.config['TWILIO_AUTH_TOKEN']
            )
            
            message = client.messages.create(
                body=notification.message,
                from_=current_app.config['TWILIO_PHONE_NUMBER'],
                to=notification.user.phone_number  # You'll need to add this to User model
            )
            
            if message.sid:
                notification.mark_as_sent()
                return True
            return False
            
        except Exception as e:
            current_app.logger.error(f"Error sending SMS notification: {str(e)}")
            notification.mark_as_failed()
            return False
    
    def send_email_notification(self, notification: Notification) -> bool:
        """Send email notification."""
        # TODO: Implement email sending functionality
        # This would use Flask-Mail or similar
        return False
    
    def get_user_notifications(self, user: Union[User, int], limit: int = 10) -> List[Notification]:
        """Get recent notifications for a user.
        
        Args:
            user: Either a User object or a user ID
            limit: Maximum number of notifications to return
        """
        user_id = user.id if isinstance(user, User) else user
        return Notification.query.filter_by(
            user_id=user_id
        ).order_by(
            Notification.created_at.desc()
        ).limit(limit).all()
    
    def mark_notification_read(self, notification_id: int, user_id: int) -> bool:
        """Mark a notification as read."""
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=user_id
        ).first()
        
        if notification:
            notification.status = 'read'
            db.session.commit()
            return True
        return False 