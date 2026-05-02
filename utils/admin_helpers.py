"""
Admin helper functions for 734 Hotel
"""
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
import json

def get_admin_statistics():
    """
    Get statistics for admin dashboard
    """
    from website.models import Booking, ContactMessage, GuestbookEntry
    
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    stats = {
        # Today's stats
        'today_bookings': Booking.objects.filter(created_at__date=today).count(),
        'today_messages': ContactMessage.objects.filter(created_at__date=today).count(),
        
        # Weekly stats
        'week_bookings': Booking.objects.filter(created_at__gte=week_ago).count(),
        'week_messages': ContactMessage.objects.filter(created_at__gte=week_ago).count(),
        
        # Monthly stats
        'month_bookings': Booking.objects.filter(created_at__gte=month_ago).count(),
        'month_messages': ContactMessage.objects.filter(created_at__gte=month_ago).count(),
        
        # Totals
        'total_bookings': Booking.objects.count(),
        'total_messages': ContactMessage.objects.count(),
        'total_guestbook': GuestbookEntry.objects.count(),
        
        # Status counts
        'pending_bookings': Booking.objects.filter(status='pending').count(),
        'confirmed_bookings': Booking.objects.filter(status='confirmed').count(),
        'new_messages': ContactMessage.objects.filter(status='new').count(),
        'unapproved_guestbook': GuestbookEntry.objects.filter(is_approved=False).count(),
    }
    
    return stats

def get_recent_activity(limit=10):
    """
    Get recent activity for admin dashboard
    """
    from website.models import Booking, ContactMessage, Notification
    
    activities = []
    
    # Recent bookings
    recent_bookings = Booking.objects.select_related('room').order_by('-created_at')[:5]
    for booking in recent_bookings:
        activities.append({
            'type': 'booking',
            'title': f'New booking from {booking.guest_name}',
            'description': f'Booked {booking.room.name} for {booking.check_in} to {booking.check_out}',
            'time': booking.created_at,
            'url': f'/admin/website/booking/{booking.id}/change/',
            'icon': 'bed'
        })
    
    # Recent messages
    recent_messages = ContactMessage.objects.order_by('-created_at')[:5]
    for message in recent_messages:
        activities.append({
            'type': 'message',
            'title': f'New message from {message.name}',
            'description': f'Subject: {message.subject}',
            'time': message.created_at,
            'url': f'/admin/website/contactmessage/{message.id}/change/',
            'icon': 'envelope'
        })
    
    # Sort by time
    activities.sort(key=lambda x: x['time'], reverse=True)
    
    return activities[:limit]

def export_data(model_name, format='json'):
    """
    Export data from specified model
    """
    from website.models import (
        Booking, ContactMessage, GuestbookEntry, 
        Room, VibeCheckItem, NeighborhoodPoint
    )
    
    model_map = {
        'booking': Booking,
        'contact': ContactMessage,
        'guestbook': GuestbookEntry,
        'room': Room,
        'vibe': VibeCheckItem,
        'neighborhood': NeighborhoodPoint,
    }
    
    if model_name not in model_map:
        return None, f"Unknown model: {model_name}"
    
    model = model_map[model_name]
    queryset = model.objects.all()
    
    if format == 'json':
        data = list(queryset.values())
        return data, None
    elif format == 'csv':
        # Basic CSV export
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        if queryset.exists():
            first_obj = queryset.first()
            writer.writerow([field.name for field in first_obj._meta.fields])
            
            # Write data
            for obj in queryset:
                writer.writerow([getattr(obj, field.name) for field in obj._meta.fields])
        
        return output.getvalue(), None
    
    return None, f"Unsupported format: {format}"

def backup_database():
    """
    Create a backup of important data
    """
    from website.models import (
        SiteSettings, HeroSection, VibeCheckItem,
        Room, NeighborhoodPoint, SocialMedia,
        AnimationSetting, CustomStyle
    )
    
    backup_data = {
        'timestamp': timezone.now().isoformat(),
        'site_settings': list(SiteSettings.objects.values()),
        'hero_sections': list(HeroSection.objects.values()),
        'vibe_items': list(VibeCheckItem.objects.values()),
        'rooms': list(Room.objects.values()),
        'neighborhood_points': list(NeighborhoodPoint.objects.values()),
        'social_media': list(SocialMedia.objects.values()),
        'animations': list(AnimationSetting.objects.values()),
        'custom_styles': list(CustomStyle.objects.values()),
    }
    
    return json.dumps(backup_data, indent=2)

def restore_from_backup(backup_data):
    """
    Restore data from backup
    """
    try:
        data = json.loads(backup_data)
        
        # Import models
        from website.models import (
            SiteSettings, HeroSection, VibeCheckItem,
            Room, NeighborhoodPoint, SocialMedia,
            AnimationSetting, CustomStyle
        )
        
        results = {
            'success': [],
            'errors': []
        }
        
        # Restore each model
        for model_name, model_data in data.items():
            if model_name == 'timestamp':
                continue
                
            model_class = {
                'site_settings': SiteSettings,
                'hero_sections': HeroSection,
                'vibe_items': VibeCheckItem,
                'rooms': Room,
                'neighborhood_points': NeighborhoodPoint,
                'social_media': SocialMedia,
                'animations': AnimationSetting,
                'custom_styles': CustomStyle,
            }.get(model_name)
            
            if model_class:
                try:
                    # Clear existing data
                    model_class.objects.all().delete()
                    
                    # Create new objects
                    for item_data in model_data:
                        # Remove id to create new objects
                        if 'id' in item_data:
                            del item_data['id']
                        
                        model_class.objects.create(**item_data)
                    
                    results['success'].append(f"Restored {len(model_data)} {model_name}")
                except Exception as e:
                    results['errors'].append(f"Error restoring {model_name}: {str(e)}")
        
        return results
        
    except Exception as e:
        return {'errors': [f"Backup restoration failed: {str(e)}"]}

def cleanup_old_data(days_old=30):
    """
    Clean up old data (bookings, messages, etc.)
    """
    from website.models import Booking, ContactMessage, Notification, GuestbookEntry
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days_old)
    
    results = {
        'deleted': 0,
        'errors': []
    }
    
    # Delete old completed/cancelled bookings
    old_bookings = Booking.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['completed', 'cancelled']
    )
    deleted_count, _ = old_bookings.delete()
    results['deleted'] += deleted_count
    
    # Delete old archived messages
    old_messages = ContactMessage.objects.filter(
        created_at__lt=cutoff_date,
        status='archived'
    )
    deleted_count, _ = old_messages.delete()
    results['deleted'] += deleted_count
    
    # Delete old notifications
    old_notifications = Notification.objects.filter(
        created_at__lt=cutoff_date,
        is_read=True
    )
    deleted_count, _ = old_notifications.delete()
    results['deleted'] += deleted_count
    
    # Delete unapproved guestbook entries older than 7 days
    old_unapproved = GuestbookEntry.objects.filter(
        created_at__lt=cutoff_date,
        is_approved=False
    )
    deleted_count, _ = old_unapproved.delete()
    results['deleted'] += deleted_count
    
    return results

def get_system_info():
    """
    Get system information and health status
    """
    import platform
    import psutil
    from django.db import connection
    from django.conf import settings
    
    info = {
        'system': {
            'python_version': platform.python_version(),
            'django_version': '4.2.0',  # Update as needed
            'os': platform.system(),
            'os_version': platform.version(),
        },
        'resources': {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
        },
        'database': {
            'engine': settings.DATABASES['default']['ENGINE'],
            'name': settings.DATABASES['default']['NAME'],
        },
        'email': {
            'backend': settings.EMAIL_BACKEND,
            'host': settings.EMAIL_HOST,
            'port': settings.EMAIL_PORT,
        }
    }
    
    # Check database connection
    try:
        connection.ensure_connection()
        info['database']['status'] = 'connected'
    except Exception as e:
        info['database']['status'] = f'error: {str(e)}'
    
    return info