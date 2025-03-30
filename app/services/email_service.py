from flask import current_app, render_template
from flask_mail import Message
from app.core.extensions import mail
from app.models.user import User
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """Service for handling email communications."""
    
    @staticmethod
    def send_email(subject, recipients, template, **kwargs):
        """Send an email using a template."""
        try:
            logger.info(f"Preparing to send email to {recipients}")
            logger.info(f"Using template: {template}")
            
            msg = Message(
                subject=subject,
                recipients=recipients,
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            
            # Log email configuration
            logger.info(f"Mail server: {current_app.config['MAIL_SERVER']}")
            logger.info(f"Mail port: {current_app.config['MAIL_PORT']}")
            logger.info(f"Mail use TLS: {current_app.config['MAIL_USE_TLS']}")
            logger.info(f"Mail username: {current_app.config['MAIL_USERNAME']}")
            
            msg.html = render_template(f'emails/{template}.html', **kwargs)
            logger.info("Email template rendered successfully")
            
            mail.send(msg)
            logger.info("Email sent successfully")
            return True
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    def send_password_reset_email(user: User, token: str):
        """Send password reset email."""
        return EmailService.send_email(
            subject='Reset Your Password - Expiry Tracker',
            recipients=[user.email],
            template='reset_password',
            user=user,
            token=token
        )
    
    @staticmethod
    def send_daily_notification_email(user: User, items: List[Dict]):
        """Send daily notification email with items that need attention."""
        if not items:
            logger.info("No items to notify about")
            return False
            
        # Filter out test items and items that don't need attention
        items_needing_attention = [
            item for item in items 
            if not item['name'].lower().startswith('test') and 
            item['days_until_expiry'] <= 7  # Only include items expiring within 7 days
        ]
        
        if not items_needing_attention:
            logger.info("No items need attention at this time")
            return False
            
        logger.info(f"Sending daily notification email to {user.email} with {len(items_needing_attention)} items needing attention")
        return EmailService.send_email(
            subject='Daily Expiry Alert Summary',
            recipients=[user.email],
            template='daily_notification',
            user=user,
            items=items_needing_attention
        )
    
    @staticmethod
    def send_expiry_notification(user: User, item_name: str, days_until_expiry: int):
        """Send expiry notification email."""
        return EmailService.send_email(
            subject=f'Expiry Alert: {item_name}',
            recipients=[user.email],
            template='expiry_notification',
            user=user,
            item_name=item_name,
            days_until_expiry=days_until_expiry
        ) 