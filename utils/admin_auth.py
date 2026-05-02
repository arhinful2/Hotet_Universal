"""
Admin authentication and credential management utilities
"""
import secrets
import string
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest
import logging

logger = logging.getLogger(__name__)

def generate_random_password(length=12):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_admin_user(email, username=None, send_email=True):
    """Create a new admin user with random password"""
    if not username:
        username = email.split('@')[0]
    
    # Generate random password
    password = generate_random_password()
    
    # Check if user exists
    if User.objects.filter(username=username).exists():
        return False, "Username already exists"
    
    if User.objects.filter(email=email).exists():
        return False, "Email already exists"
    
    try:
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_superuser=True
        )
        
        # Send email with credentials
        if send_email:
            send_admin_credentials_email(user, password)
        
        return True, user
    except Exception as e:
        logger.error(f"Failed to create admin user: {str(e)}")
        return False, str(e)

def reset_admin_password(user, send_email=True):
    """Reset admin password and send email"""
    try:
        # Generate new password
        new_password = generate_random_password()
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        # Send email with new password
        if send_email:
            send_password_reset_email(user, new_password)
        
        return True, new_password
    except Exception as e:
        logger.error(f"Failed to reset admin password: {str(e)}")
        return False, str(e)

def send_admin_credentials_email(user, password):
    """Send email with admin credentials"""
    try:
        subject = "Your 734 Hotel Admin Portal Credentials"
        message = f"""
        Hello {user.username},
        
        Your admin account has been created successfully!
        
        Login Credentials:
        - Username: {user.username}
        - Password: {password}
        - Admin URL: {settings.SITE_URL}/admin/
        
        Please change your password after first login.
        
        Best regards,
        734 Hotel Team
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Admin credentials sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send admin credentials email: {str(e)}")
        return False

def send_password_reset_email(user, new_password=None):
    """Send password reset email"""
    try:
        if new_password:
            subject = "734 Hotel Admin - Password Reset"
            message = f"""
            Hello {user.username},
            
            Your password has been reset.
            
            New Password: {new_password}
            
            Please change your password after logging in.
            
            Login URL: {settings.SITE_URL}/admin/
            
            Best regards,
            734 Hotel Team
            """
        else:
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = f"{settings.SITE_URL}/admin/password-reset/{uid}/{token}/"
            
            subject = "734 Hotel Admin - Password Reset Request"
            message = f"""
            Hello {user.username},
            
            You requested a password reset for your admin account.
            
            Click here to reset your password: {reset_url}
            
            This link will expire in 24 hours.
            
            If you didn't request this, please ignore this email.
            
            Best regards,
            734 Hotel Team
            """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Password reset email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
        return False

def verify_admin_token(uidb64, token):
    """Verify password reset token"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        
        if default_token_generator.check_token(user, token):
            return True, user
        return False, "Invalid token"
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return False, "Invalid user"

def get_admin_statistics():
    """Get admin user statistics"""
    stats = {
        'total_admins': User.objects.filter(is_staff=True).count(),
        'active_admins': User.objects.filter(is_staff=True, is_active=True).count(),
        'superusers': User.objects.filter(is_superuser=True).count(),
        'recent_logins': User.objects.filter(last_login__isnull=False).order_by('-last_login')[:5],
    }
    return stats

def admin_action_log(request: HttpRequest, action_type: str, 
                     object_type: str = '', object_id: int = None, 
                     object_repr: str = ''):
    """Log admin actions for security"""
    from website.models import AdminActionLog
    
    try:
        AdminActionLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action_type=action_type,
            object_type=object_type,
            object_id=object_id,
            object_repr=object_repr[:200],
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
    except Exception as e:
        logger.error(f"Failed to log admin action: {str(e)}")

def create_admin_from_request(request):
    """Create admin user from HTTP request data"""
    try:
        email = request.POST.get('email')
        username = request.POST.get('username') or email.split('@')[0]
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        send_email = request.POST.get('send_email', 'true').lower() == 'true'
        
        # Generate random password
        password = generate_random_password()
        
        # Check if user exists
        if User.objects.filter(username=username).exists():
            return False, "Username already exists"
        
        if User.objects.filter(email=email).exists():
            return False, "Email already exists"
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=True,
            is_superuser=True
        )
        
        # Log the action
        admin_action_log(request, 'user_create', 'User', user.id, str(user))
        
        # Send email
        if send_email:
            send_admin_credentials_email(user, password)
            messages.success(request, f"Admin user created and email sent to {email}")
        else:
            messages.success(request, f"Admin user created. Password: {password}")
        
        return True, user
    except Exception as e:
        logger.error(f"Failed to create admin from request: {str(e)}")
        return False, str(e)