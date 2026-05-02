"""
Email sending utilities for 734 Hotel
"""
import logging
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

def send_booking_confirmation(booking):
    """
    Send booking confirmation email to guest
    """
    try:
        subject = f"Booking Confirmation - 734 Hotel (Booking #{booking.id})"
        
        # Render HTML template
        html_content = render_to_string('email/booking_confirmation.html', {
            'booking': booking,
            'domain': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
        })
        
        # Create text version
        text_content = f"""
        Booking Confirmation - 734 Hotel
        
        Dear {booking.guest_name},
        
        Your booking has been confirmed!
        
        Booking Details:
        - Booking ID: {booking.id}
        - Room: {booking.room.name}
        - Check-in: {booking.check_in}
        - Check-out: {booking.check_out}
        - Guests: {booking.number_of_guests}
        - Total: ₵{booking.total_price if booking.total_price else 'To be calculated'}
        
        Our check-in time is from 3:00 PM, and check-out is at 11:00 AM.
        
        Address: 734 Adventure Street, Travel City
        Phone: +1 (234) 567-8900
        Email: hello@734hotel.com
        
        We're looking forward to welcoming you!
        
        Best regards,
        734 Hotel Team
        """
        
        # Send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[booking.guest_email],
            reply_to=[settings.DEFAULT_FROM_EMAIL]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        # Update booking record
        booking.email_sent = True
        booking.save()
        
        logger.info(f"Booking confirmation sent to {booking.guest_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send booking confirmation: {str(e)}")
        return False

def send_admin_notification(subject, message, notification_type='system'):
    """
    Send notification email to admin
    """
    try:
        site_settings = None
        try:
            from website.models import SiteSettings
            site_settings = SiteSettings.objects.first()
        except:
            pass
        
        recipient = site_settings.notification_email if site_settings else settings.ADMIN_EMAIL
        
        if not recipient:
            logger.warning("No admin email configured for notifications")
            return False
        
        send_mail(
            subject=f"[734 Hotel] {subject}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        
        logger.info(f"Admin notification sent: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send admin notification: {str(e)}")
        return False

def send_contact_reply(contact_message, reply_text):
    """
    Send reply to contact message
    """
    try:
        subject = f"Re: {contact_message.subject}"
        
        message = f"""
        Dear {contact_message.name},
        
        Thank you for contacting 734 Hotel.
        
        {reply_text}
        
        Best regards,
        734 Hotel Team
        
        ---
        Original message:
        Subject: {contact_message.subject}
        Message: {contact_message.message}
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[contact_message.email],
            fail_silently=False,
        )
        
        logger.info(f"Contact reply sent to {contact_message.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send contact reply: {str(e)}")
        return False

def send_welcome_email(email, name):
    """
    Send welcome email to newsletter subscribers or new accounts
    """
    try:
        subject = "Welcome to 734 Hotel Community!"
        
        html_content = render_to_string('email/welcome.html', {
            'name': name,
            'domain': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
        })
        
        text_content = f"""
        Welcome to 734 Hotel, {name}!
        
        Thank you for joining our community of travelers.
        
        Stay updated on:
        - Special offers and discounts
        - Community events
        - Travel tips and stories
        - New features at 734 Hotel
        
        Follow our journey on social media for daily inspiration!
        
        Best regards,
        734 Hotel Team
        """
        
        email_msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )
        email_msg.attach_alternative(html_content, "text/html")
        email_msg.send()
        
        logger.info(f"Welcome email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")
        return False

def send_custom_email(to_email, subject, html_content, text_content=None):
    """
    Send custom email with HTML support
    """
    try:
        if text_content is None:
            text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f"Custom email sent to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send custom email: {str(e)}")
        return False

def test_email_configuration():
    """
    Test email configuration by sending a test email
    """
    try:
        send_mail(
            subject="734 Hotel - Email Configuration Test",
            message="This is a test email from 734 Hotel system.\n\nIf you received this, your email configuration is working correctly!",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=False,
        )
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)