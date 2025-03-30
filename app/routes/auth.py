from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.core.extensions import db, login_manager
from app.models.user import User
from app.services.zoho_service import ZohoService
from app.services.email_service import EmailService
from datetime import datetime, timedelta
import jwt
from typing import Optional

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
        zoho_service.logout()
        flash('Successfully disconnected from Zoho', 'success')
    except Exception as e:
        flash(f'Error disconnecting from Zoho: {str(e)}', 'error')
    
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

def verify_password_reset_token(token: str) -> Optional[User]:
    """Verify a password reset token."""
    try:
        data = jwt.decode(
            token,
            current_app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        return User.query.get(data['user_id'])
    except:
        return None

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password request."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = generate_password_reset_token(user)
            if EmailService.send_password_reset_email(user, token):
                flash('Password reset instructions have been sent to your email', 'success')
            else:
                flash('Error sending password reset email. Please try again.', 'error')
        else:
            flash('Email address not found', 'error')
    
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    user = verify_password_reset_token(token)
    if not user:
        flash('Invalid or expired password reset link', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/reset_password.html')
        
        try:
            user.set_password(password)
            user.save()
            flash('Your password has been reset successfully', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'Error resetting password: {str(e)}', 'error')
    
    return render_template('auth/reset_password.html') 