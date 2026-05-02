from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .models import Booking, ContactMessage, GuestbookEntry, Notification, SiteSettings

@receiver(post_save, sender=Booking)
def booking_created(sender, instance, created, **kwargs):
    """Create notification when booking is created"""
    if created:
        site_settings = SiteSettings.objects.first()
        if site_settings and site_settings.enable_email_notifications:
            # Create notification
            Notification.objects.create(
                notification_type='booking',
                title=f'New Booking from {instance.guest_name}',
                message=f'New booking for {instance.room.name}',
                related_object_id=instance.id,
                related_object_type='booking'
            )

@receiver(post_save, sender=ContactMessage)
def contact_message_created(sender, instance, created, **kwargs):
    """Create notification when contact message is created"""
    if created:
        site_settings = SiteSettings.objects.first()
        if site_settings and site_settings.enable_email_notifications:
            Notification.objects.create(
                notification_type='contact',
                title=f'New Message from {instance.name}',
                message=instance.subject,
                related_object_id=instance.id,
                related_object_type='contact'
            )

@receiver(post_save, sender=GuestbookEntry)
def guestbook_entry_created(sender, instance, created, **kwargs):
    """Create notification when guestbook entry is created"""
    if created:
        site_settings = SiteSettings.objects.first()
        if site_settings and site_settings.enable_email_notifications:
            Notification.objects.create(
                notification_type='guestbook',
                title=f'New Guestbook Entry from {instance.name}',
                message=instance.message[:100] + '...',
                related_object_id=instance.id,
                related_object_type='guestbook'
            )

def create_notification(notification_type, title, message, related_object_id=None, related_object_type=None):
    """Helper function to create notifications"""
    Notification.objects.create(
        notification_type=notification_type,
        title=title,
        message=message,
        related_object_id=related_object_id,
        related_object_type=related_object_type
    )