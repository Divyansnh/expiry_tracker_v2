from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.core.extensions import db, login_manager
from app.models.user import User
from app.models.base import db
from app.services.zoho_service import ZohoService
from app.services.email_service import EmailService
from datetime import datetime, timedelta
import jwt
from typing import Optional
from app.forms.reset_password_request_form import ResetPasswordRequestForm
from app.forms.reset_password_form import ResetPasswordForm

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.query.get(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        
        flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('auth/register.html')
        
        try:
            user = User(username=username, email=email)
            user.set_password(password)
            user.save()
            
            login_user(user)
            flash('Registration successful!', 'success')
            return redirect(url_for('main.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error during registration: {str(e)}', 'error')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    return redirect(url_for('main.index'))

@auth_bp.route('/zoho/login')
@login_required
def zoho_login():
    """Initiate Zoho OAuth login."""
    try:
        zoho_service = ZohoService()
        auth_url = zoho_service.get_auth_url()
        return redirect(auth_url)
    except Exception as e:
        flash(f'Error connecting to Zoho: {str(e)}', 'error')
        return redirect(url_for('main.settings'))

@auth_bp.route('/zoho/callback')
@login_required
def zoho_callback():
    """Handle Zoho OAuth callback."""
    try:
        zoho_service = ZohoService()
        code = request.args.get('code')
        if not code:
            flash('No authorization code received from Zoho', 'error')
            return redirect(url_for('main.settings'))
        
        success = zoho_service.handle_callback(code)
        if success:
            flash('Successfully connected to Zoho!', 'success')
        else:
            flash('Failed to connect to Zoho', 'error')
        
        return redirect(url_for('main.settings'))
        
    except Exception as e:
        flash(f'Error during Zoho callback: {str(e)}', 'error')
        return redirect(url_for('main.settings'))

@auth_bp.route('/zoho/logout')
@login_required
def zoho_logout():
    """Logout from Zoho."""
    try:
        zoho_service = ZohoService()
        if zoho_service.logout():
            flash('Successfully disconnected from Zoho', 'success')
        else:
            flash('Error disconnecting from Zoho', 'error')
    except Exception as e:
        current_app.logger.error(f"Error in Zoho logout: {str(e)}")
        flash('Error disconnecting from Zoho', 'error')
    
    return redirect(url_for('main.settings'))

def generate_password_reset_token(user: User) -> str:
    """Generate a password reset token."""
    return jwt.encode(
        {
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(hours=1)
        },
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )

def verify_password_reset_token(token: str, invalidate: bool = True) -> Optional[User]:
    """Verify a password reset token."""
    try:
        data = jwt.decode(
            token,
            current_app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        user = User.query.get(data['user_id'])
        if invalidate:
            user.invalidate_reset_token()
        return user
    except:
        return None

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password request."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # Invalidate any existing reset tokens
            user.invalidate_reset_token()
            # Generate new token
            token = user.get_password_reset_token()
            user.password_reset_token = token
            db.session.commit()
            
            # Send reset email
            email_service = EmailService()
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            email_service.send_password_reset_email(user.email, reset_url)
            
            # Always show the same message regardless of whether the email exists
            flash('If an account exists with this email, you will receive password reset instructions.')
            return redirect(url_for('auth.login'))
        else:
            # Don't reveal whether the email exists
            flash('If an account exists with this email, you will receive password reset instructions.')
            return redirect(url_for('auth.login'))
            
    return render_template('auth/forgot_password.html', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    try:
        # On GET request, just verify the token is valid but don't invalidate it
        if request.method == 'GET':
            user = User.verify_password_reset_token(token, invalidate=False)
            if not user:
                current_app.logger.warning(f"Invalid or expired password reset token: {token}")
                flash('Invalid or expired password reset link')
                return redirect(url_for('auth.forgot_password'))
            return render_template('auth/reset_password.html', form=ResetPasswordForm())
            
        # On POST request, verify and invalidate the token
        user = User.verify_password_reset_token(token, invalidate=True)
        if not user:
            current_app.logger.warning(f"Invalid or expired password reset token: {token}")
            flash('Invalid or expired password reset link')
            return redirect(url_for('auth.forgot_password'))
            
        form = ResetPasswordForm()
        if form.validate_on_submit():
            user.set_password(form.password.data)
            # Invalidate the used token
            user.invalidate_reset_token()
            db.session.commit()
            
            # Send confirmation email
            email_service = EmailService()
            email_service.send_password_reset_confirmation(user.email)
            
            flash('Your password has been reset successfully')
            return redirect(url_for('auth.login'))
            
        return render_template('auth/reset_password.html', form=form)
    except Exception as e:
        current_app.logger.error(f"Error during password reset: {str(e)}")
        flash('An error occurred while processing your request')
        return redirect(url_for('auth.forgot_password')) 