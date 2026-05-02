from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from colorfield.fields import ColorField
from django_ckeditor_5.fields import CKEditor5Field
import json
import uuid
from django.core.serializers.json import DjangoJSONEncoder


class SiteSettings(models.Model):
    """Global site settings managed from admin"""
    site_name = models.CharField(max_length=200, default="734 Hotel")
    tagline = models.CharField(
        max_length=500, default="Your basecamp for good stories")
    description = models.TextField(blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)
    og_image = models.ImageField(upload_to='logos/', blank=True, null=True)

    # Logo management
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    favicon = models.ImageField(upload_to='logos/', blank=True, null=True)

    # Social Media
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    tripadvisor_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)

    # Color Theme Management
    primary_color = ColorField(default='#E76F51')
    secondary_color = ColorField(default='#2A9D8F')
    accent_color = ColorField(default='#E9C46A')
    background_color = ColorField(default='#F8F9FA')
    text_color = ColorField(default='#264653')

    # Typography
    font_family = models.CharField(
        max_length=200, default="'Inter', sans-serif")
    heading_font = models.CharField(
        max_length=200, default="'Cabin', sans-serif")

    # Animation Settings
    enable_animations = models.BooleanField(default=True)
    animation_speed = models.CharField(max_length=20, choices=[
        ('slow', 'Slow'),
        ('normal', 'Normal'),
        ('fast', 'Fast')
    ], default='normal')
    motion_intensity = models.CharField(max_length=20, choices=[
        ('soft', 'Soft'),
        ('balanced', 'Balanced'),
        ('strong', 'Strong')
    ], default='balanced')
    scroll_smoothness = models.CharField(max_length=20, choices=[
        ('gentle', 'Gentle'),
        ('normal', 'Normal'),
        ('enhanced', 'Enhanced')
    ], default='normal')

    # Feature Toggles
    enable_vibe_check = models.BooleanField(default=True)
    enable_guestbook = models.BooleanField(default=True)
    enable_booking = models.BooleanField(default=True)
    enable_map = models.BooleanField(default=True)
    enable_datepicker = models.BooleanField(default=True)

    # Layout Settings
    layout_style = models.CharField(max_length=50, choices=[
        ('standard', 'Standard'),
        ('minimal', 'Minimal'),
        ('cozy', 'Cozy')
    ], default='cozy')

    # Custom CSS (for advanced users)
    custom_css = models.TextField(blank=True)

    # Email Settings
    notification_email = models.EmailField(default='admin@734hotel.com')
    enable_email_notifications = models.BooleanField(default=True)

    # Meta fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return f"Site Settings - {self.site_name}"


class SEOPage(models.Model):
    MATCH_TYPE_CHOICES = [
        ('exact', 'Exact Path Match'),
        ('prefix', 'Path Prefix Match'),
    ]

    name = models.CharField(max_length=120)
    path = models.CharField(
        max_length=255,
        help_text="Use URL path only. Example: / for homepage, /room/ for all room pages."
    )
    match_type = models.CharField(
        max_length=10,
        choices=MATCH_TYPE_CHOICES,
        default='exact'
    )
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)
    canonical_url = models.URLField(blank=True)
    robots_index = models.BooleanField(default=True)
    robots_follow = models.BooleanField(default=True)

    og_title = models.CharField(max_length=90, blank=True)
    og_description = models.CharField(max_length=320, blank=True)
    og_image = models.ImageField(upload_to='logos/', blank=True, null=True)
    twitter_card = models.CharField(
        max_length=30, default='summary_large_image')

    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(
        default=100,
        help_text="Lower number = higher priority when multiple prefix rules match."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SEO Page Rule"
        verbose_name_plural = "SEO Page Rules"
        ordering = ['priority', '-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['path', 'match_type'],
                name='unique_seo_path_match_type'
            )
        ]

    def clean(self):
        super().clean()
        if not self.path:
            raise ValidationError({'path': 'Path is required.'})

        normalized = self.path.strip()
        if not normalized.startswith('/'):
            normalized = f'/{normalized}'

        if self.match_type == 'prefix' and not normalized.endswith('/'):
            normalized = f'{normalized}/'

        self.path = normalized

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def robots_content(self):
        return f"{'index' if self.robots_index else 'noindex'}, {'follow' if self.robots_follow else 'nofollow'}"

    def __str__(self):
        return f"{self.name} ({self.match_type}: {self.path})"


class HeroSection(models.Model):
    title = models.CharField(max_length=200, blank=True)
    subtitle = models.CharField(max_length=500, blank=True)
    background_image = models.ImageField(upload_to='hero/', blank=True)
    overlay_opacity = models.IntegerField(
        default=30,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    button_text = models.CharField(max_length=50, default="Book Now")
    button_link = models.CharField(max_length=200, default="#booking")
    is_active = models.BooleanField(default=True)

    # Animation settings
    enable_title_animation = models.BooleanField(default=True)
    title_animation_type = models.CharField(max_length=50, default='fadeInUp')
    enable_subtitle_animation = models.BooleanField(default=True)
    subtitle_animation_delay = models.IntegerField(default=500)

    order = models.IntegerField(default=1)

    class Meta:
        verbose_name = "Hero Section"
        verbose_name_plural = "Hero Sections"
        ordering = ['order']

    def __str__(self):
        return self.title or "Hero Section"


class VibeCheckItem(models.Model):
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='vibe_check/')
    audio_file = models.FileField(upload_to='audio/', blank=True, null=True)
    audio_url = models.URLField(blank=True)
    description = models.TextField()
    guest_note = models.TextField(blank=True)
    guest_name = models.CharField(max_length=100, blank=True)
    guest_country = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Vibe Check Item"
        verbose_name_plural = "Vibe Check Items"

    def __str__(self):
        return self.title


class Room(models.Model):
    ROOM_TYPES = [
        ('dorm', 'Dormitory'),
        ('private', 'Private Room'),
        ('suite', 'Suite'),
        ('family', 'Family Room'),
    ]

    name = models.CharField(max_length=100)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    description = CKEditor5Field()
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.IntegerField()
    available_beds = models.IntegerField()
    main_image = models.ImageField(upload_to='rooms/')

    # Features
    features = models.JSONField(default=list, encoder=DjangoJSONEncoder)

    # Display settings
    color_accent = ColorField(default='#2A9D8F')
    is_featured = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    # Hover effects
    hover_effect = models.CharField(max_length=50, choices=[
        ('scale', 'Scale Up'),
        ('slide', 'Slide Up'),
        ('rotate', 'Rotate'),
        ('shadow', 'Shadow Lift')
    ], default='scale')

    class Meta:
        ordering = ['order', 'price_per_night']
        verbose_name = "Room"
        verbose_name_plural = "Rooms"

    def __str__(self):
        return f"{self.name} - {self.get_room_type_display()}"


class NeighborhoodPoint(models.Model):
    POINT_TYPES = [
        ('food', 'Food & Drink'),
        ('entertainment', 'Entertainment'),
        ('culture', 'Cultural'),
        ('shopping', 'Shopping'),
        ('nature', 'Nature'),
        ('transport', 'Transport'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    point_type = models.CharField(max_length=20, choices=POINT_TYPES)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    icon = models.CharField(max_length=50, default='pin')
    color = ColorField(default='#E76F51')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Neighborhood Point"
        verbose_name_plural = "Neighborhood Points"

    def __str__(self):
        return self.title


class GuestbookEntry(models.Model):
    name = models.CharField(max_length=100)
    hometown = models.CharField(max_length=100)
    message = models.TextField()
    color = ColorField(default='#E9C46A')
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Guestbook Entry"
        verbose_name_plural = "Guestbook Entries"

    def __str__(self):
        return f"Entry by {self.name}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    # Guest Information
    guest_name = models.CharField(max_length=200)
    guest_email = models.EmailField()
    guest_phone = models.CharField(max_length=20, blank=True)
    guest_country = models.CharField(max_length=100, blank=True)

    # Booking Details
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='bookings')
    check_in = models.DateField()
    check_out = models.DateField()
    number_of_guests = models.IntegerField(default=1)
    special_requests = models.TextField(blank=True)

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    guest_access_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Communication
    admin_notes = models.TextField(blank=True)
    email_sent = models.BooleanField(default=False)
    email_replies = models.JSONField(
        default=list, blank=True, encoder=DjangoJSONEncoder)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"

    def __str__(self):
        return f"Booking #{self.id} - {self.guest_name}"


class PaymentSettings(models.Model):
    enable_online_payment = models.BooleanField(default=False)
    auto_confirm_booking_on_payment = models.BooleanField(default=True)
    allow_guest_changes_after_payment = models.BooleanField(default=False)
    default_currency = models.CharField(max_length=10, default='GHS')
    success_redirect_path = models.CharField(
        max_length=200,
        default='/payment/success/'
    )
    cancel_redirect_path = models.CharField(
        max_length=200,
        default='/payment/cancel/'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment Settings"
        verbose_name_plural = "Payment Settings"

    def __str__(self):
        return "Payment Settings"


class PaymentProviderConfig(models.Model):
    PROVIDER_CHOICES = [
        ('stripe', 'Stripe'),
        ('paystack', 'Paystack'),
        ('paypal', 'PayPal'),
        ('momo', 'Mobile Money (Custom URL/API)'),
        ('custom', 'Custom Provider'),
    ]

    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    display_name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    priority = models.PositiveIntegerField(default=100)
    public_key = models.CharField(max_length=255, blank=True)
    secret_key = models.CharField(max_length=255, blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    api_base_url = models.URLField(blank=True)
    callback_url = models.URLField(blank=True)
    checkout_url_template = models.TextField(
        blank=True,
        help_text="For momo/custom: use placeholders {amount}, {amount_minor}, {email}, {reference}, {currency}, {callback_url}."
    )
    extra_config = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Payment Provider"
        verbose_name_plural = "Payment Providers"
        ordering = ['priority', 'display_name']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            PaymentProviderConfig.objects.exclude(
                pk=self.pk).update(is_default=False)

    def __str__(self):
        return f"{self.display_name} ({self.get_provider_display()})"


class BookingPayment(models.Model):
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('pending', 'Pending Verification'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    provider = models.ForeignKey(
        PaymentProviderConfig,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='GHS')
    reference = models.CharField(max_length=64, unique=True)
    external_reference = models.CharField(max_length=255, blank=True)
    checkout_url = models.URLField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='initiated'
    )
    provider_response = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Booking Payment"
        verbose_name_plural = "Booking Payments"

    def __str__(self):
        return f"{self.reference} - {self.booking.guest_name}"


class ContactMessage(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('archived', 'Archived'),
    ]

    name = models.CharField(max_length=200)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='new')

    # Admin response tracking
    admin_response = models.TextField(blank=True)
    reply_history = models.JSONField(
        default=list, blank=True, encoder=DjangoJSONEncoder)
    admin_responded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)
    admin_responded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('booking', 'New Booking'),
        ('contact', 'New Contact Message'),
        ('guestbook', 'New Guestbook Entry'),
        ('system', 'System Notification'),
    ]

    notification_type = models.CharField(
        max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_object_id = models.IntegerField(null=True, blank=True)
    related_object_type = models.CharField(max_length=100, blank=True)

    # For admin portal
    is_read = models.BooleanField(default=False)
    read_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='read_notifications')
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.title}"


class SocialMedia(models.Model):
    PLATFORMS = [
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter'),
        ('tripadvisor', 'TripAdvisor'),
        ('youtube', 'YouTube'),
        ('linkedin', 'LinkedIn'),
        ('pinterest', 'Pinterest'),
        ('tiktok', 'TikTok'),
    ]
    site_settings = models.ForeignKey(
        'SiteSettings',  # Reference to SiteSettings model
        on_delete=models.CASCADE,  # If SiteSettings is deleted, delete related SocialMedia
        related_name='social_media',  # Name to access from SiteSettings
        null=True,  # Allow existing records to be null
        blank=True,  # Allow form submission without this field
        help_text="Link to site settings")

    platform = models.CharField(max_length=20, choices=PLATFORMS)
    url = models.URLField()
    icon_class = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('site_settings', 'platform')
        ordering = ['order']
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Social Media"
        verbose_name_plural = "Social Media"

    def __str__(self):
        return f"{self.get_platform_display()}"


class AnimationSetting(models.Model):
    ANIMATION_TYPES = [
        ('fade', 'Fade'),
        ('slide', 'Slide'),
        ('zoom', 'Zoom'),
        ('bounce', 'Bounce'),
        ('rotate', 'Rotate'),
        ('flip', 'Flip'),
    ]

    # ADD THIS FOREIGNKEY FIELD:
    site_settings = models.ForeignKey(
        'SiteSettings',  # Reference to SiteSettings model
        on_delete=models.CASCADE,  # If SiteSettings is deleted, delete related AnimationSetting
        related_name='animation_settings',  # Name to access from SiteSettings
        null=True,  # Allow existing records to be null
        blank=True,  # Allow form submission without this field
        help_text="Link to site settings")

    element = models.CharField(max_length=100)
    animation_type = models.CharField(max_length=20, choices=ANIMATION_TYPES)
    duration = models.IntegerField(default=1000)  # in milliseconds
    delay = models.IntegerField(default=0)  # in milliseconds
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ('site_settings', 'element')

    class Meta:
        verbose_name = "Animation Setting"
        verbose_name_plural = "Animation Settings"

    def __str__(self):
        return f"{self.element} - {self.animation_type}"


class CustomStyle(models.Model):
    name = models.CharField(max_length=100)
    css_class = models.CharField(max_length=100, unique=True)
    css_code = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Custom Style"
        verbose_name_plural = "Custom Styles"

    def __str__(self):
        return self.name


class RoomImage(models.Model):
    """Multiple images for a room"""
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='room_images')
    image = models.ImageField(upload_to='rooms/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Room Image"
        verbose_name_plural = "Room Images"

    def __str__(self):
        return f"Image for {self.room.name}"


class EmailConfig(models.Model):
    """Email configuration managed from admin"""
    PROTOCOL_CHOICES = [
        ('tls', 'TLS'),
        ('ssl', 'SSL'),
        ('none', 'None'),
    ]

    site_settings = models.ForeignKey(
        SiteSettings,
        on_delete=models.CASCADE,
        related_name='email_configs',
        null=True,
        blank=True
    )

    # SMTP Settings
    email_backend = models.CharField(
        max_length=50,
        default='django.core.mail.backends.smtp.EmailBackend'
    )
    email_host = models.CharField(max_length=255, default='smtp.gmail.com')
    email_port = models.IntegerField(default=587)
    email_protocol = models.CharField(
        max_length=10, choices=PROTOCOL_CHOICES, default='tls')
    email_use_tls = models.BooleanField(default=True)
    email_use_ssl = models.BooleanField(default=False)

    # Credentials
    email_host_user = models.CharField(max_length=255)
    email_host_password = models.CharField(max_length=255)
    default_from_email = models.EmailField(default='noreply@734hotel.com')

    # Templates
    booking_confirmation_template = models.TextField(
        blank=True, default='Dear {guest_name},\n\nYour booking has been confirmed.')
    booking_cancellation_template = models.TextField(blank=True)
    contact_reply_template = models.TextField(blank=True)

    # Settings
    send_booking_emails = models.BooleanField(default=True)
    send_contact_emails = models.BooleanField(default=True)
    send_newsletter = models.BooleanField(default=False)

    # Test email
    test_email_address = models.EmailField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Email Configuration"
        verbose_name_plural = "Email Configurations"

    def __str__(self):
        return f"Email Config: {self.email_host}"

    def save(self, *args, **kwargs):
        # Update Django settings when email config is saved
        if self.is_active:
            # This would update settings, but careful with this in production
            pass
        super().save(*args, **kwargs)


class SMSConfig(models.Model):
    """SMS configuration managed from admin"""
    PROVIDER_CHOICES = [
        ('twilio', 'Twilio'),
        ('plivo', 'Plivo'),
        ('nexmo', 'Nexmo/Vonage'),
        ('arkesel', 'Arkesel'),
        ('custom', 'Custom API'),
    ]

    site_settings = models.ForeignKey(
        SiteSettings,
        on_delete=models.CASCADE,
        related_name='sms_configs',
        null=True,
        blank=True
    )

    provider = models.CharField(
        max_length=20, choices=PROVIDER_CHOICES, default='twilio')

    # API Credentials
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    account_sid = models.CharField(max_length=255, blank=True)  # For Twilio
    auth_token = models.CharField(max_length=255, blank=True)   # For Twilio
    from_number = models.CharField(max_length=20, blank=True)

    # API Endpoints
    api_url = models.URLField(blank=True)

    # Templates
    booking_sms_template = models.TextField(
        blank=True, default='Hi there, your booking at 734 Hotel is confirmed. We will contact you soon with details.')
    reminder_sms_template = models.TextField(blank=True)

    # Settings
    send_booking_sms = models.BooleanField(default=False)
    send_reminder_sms = models.BooleanField(default=False)
    send_promotional_sms = models.BooleanField(default=False)

    # Test
    test_phone_number = models.CharField(max_length=20, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SMS Configuration"
        verbose_name_plural = "SMS Configurations"

    def __str__(self):
        return f"SMS Config: {self.get_provider_display()}"


class ServiceItem(models.Model):
    """Service cards shown on the website and managed from admin"""
    title = models.CharField(max_length=120)
    description = models.TextField()
    icon_class = models.CharField(
        max_length=100, default='fas fa-concierge-bell')
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Service Item"
        verbose_name_plural = "Service Items"

    def __str__(self):
        return self.title


class DatabaseConfig(models.Model):
    """Database connection settings managed from admin"""
    ENGINE_CHOICES = [
        ('sqlite', 'SQLite (Default)'),
        ('postgresql', 'PostgreSQL'),
    ]

    engine = models.CharField(
        max_length=20, choices=ENGINE_CHOICES, default='sqlite')
    sqlite_name = models.CharField(
        max_length=255, default='db.sqlite3', blank=True)

    postgres_name = models.CharField(max_length=255, blank=True)
    postgres_user = models.CharField(max_length=255, blank=True)
    postgres_password = models.CharField(max_length=255, blank=True)
    postgres_host = models.CharField(max_length=255, blank=True)
    postgres_port = models.CharField(max_length=10, default='5432', blank=True)

    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Database Configuration"
        verbose_name_plural = "Database Configurations"

    def __str__(self):
        return f"Database: {self.get_engine_display()}"


# Add these models AFTER your existing models in models.py
class NewsletterSubscription(models.Model):
    """Newsletter subscription model"""
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    confirmation_token = models.CharField(max_length=100, blank=True)
    is_confirmed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Newsletter Subscription"
        verbose_name_plural = "Newsletter Subscriptions"

    def __str__(self):
        return self.email


class Review(models.Model):
    """Room reviews/ratings system"""
    RATING_CHOICES = [
        (1, '★☆☆☆☆'),
        (2, '★★☆☆☆'),
        (3, '★★★☆☆'),
        (4, '★★★★☆'),
        (5, '★★★★★'),
    ]

    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)
    guest_name = models.CharField(max_length=100)
    guest_email = models.EmailField(blank=True)
    rating = models.IntegerField(choices=RATING_CHOICES, default=5)
    title = models.CharField(max_length=200)
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)
    helpful_yes = models.IntegerField(default=0)
    helpful_no = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Review"
        verbose_name_plural = "Reviews"

    def __str__(self):
        return f"Review by {self.guest_name} for {self.room.name}"


class Wishlist(models.Model):
    """User wishlist/favorites system"""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='wishlist')
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['user', 'room']
        verbose_name = "Wishlist Item"
        verbose_name_plural = "Wishlist Items"

    def __str__(self):
        return f"{self.user.username} - {self.room.name}"


class PhotoGallery(models.Model):
    """Photo gallery section"""
    CATEGORY_CHOICES = [
        ('hotel', 'Hotel'),
        ('rooms', 'Rooms'),
        ('events', 'Events'),
        ('food', 'Food & Drink'),
        ('people', 'People'),
        ('neighborhood', 'Neighborhood'),
    ]

    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='gallery/')
    caption = models.TextField(blank=True)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default='hotel')
    is_featured = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-uploaded_at']
        verbose_name = "Gallery Photo"
        verbose_name_plural = "Gallery Photos"

    def __str__(self):
        return self.title


class Event(models.Model):
    """Events/activities calendar"""
    EVENT_TYPES = [
        ('workshop', 'Workshop'),
        ('social', 'Social Event'),
        ('tour', 'Tour'),
        ('food', 'Food & Drink'),
        ('music', 'Music'),
        ('art', 'Art & Culture'),
        ('wellness', 'Wellness'),
    ]

    title = models.CharField(max_length=200)
    description = CKEditor5Field()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    location = models.CharField(max_length=200)
    image = models.ImageField(upload_to='events/', blank=True, null=True)
    max_attendees = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_free = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_date']
        verbose_name = "Event"
        verbose_name_plural = "Events"

    def __str__(self):
        return self.title


class EventRegistration(models.Model):
    """Event registrations"""
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name='registrations')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    number_of_guests = models.IntegerField(default=1)
    special_requests = models.TextField(blank=True)
    is_confirmed = models.BooleanField(default=False)
    confirmation_token = models.CharField(max_length=100, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Event Registration"
        verbose_name_plural = "Event Registrations"

    def __str__(self):
        return f"{self.name} - {self.event.title}"


class BlogPost(models.Model):
    """Blog/news section"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)
    excerpt = models.TextField()
    content = CKEditor5Field()
    featured_image = models.ImageField(upload_to='blog/')
    category = models.CharField(max_length=50, default='News')
    tags = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)
    views = models.IntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class BlogComment(models.Model):
    """Blog post comments"""
    blog_post = models.ForeignKey(
        BlogPost, on_delete=models.CASCADE, related_name='comments')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Blog Comment"
        verbose_name_plural = "Blog Comments"

    def __str__(self):
        return f"Comment by {self.name} on {self.blog_post.title}"


class CacheSetting(models.Model):
    """Cache configuration for better performance"""
    CACHE_BACKENDS = [
        ('django.core.cache.backends.locmem.LocMemCache', 'Local Memory'),
        ('django.core.cache.backends.filebased.FileBasedCache', 'File Based'),
        ('django.core.cache.backends.db.DatabaseCache', 'Database'),
        ('django.core.cache.backends.memcached.MemcachedCache', 'Memcached'),
    ]

    cache_backend = models.CharField(max_length=100, choices=CACHE_BACKENDS,
                                     default='django.core.cache.backends.locmem.LocMemCache')
    default_timeout = models.IntegerField(
        default=300, help_text="Cache timeout in seconds")
    is_enabled = models.BooleanField(default=True)

    # For file based cache
    cache_location = models.CharField(
        max_length=200, blank=True, help_text="Directory for file cache")

    # For database cache
    cache_table = models.CharField(
        max_length=100, default='cache_table', blank=True)

    # For memcached
    cache_url = models.CharField(
        max_length=200, blank=True, help_text="Memcached server URL")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cache Setting"
        verbose_name_plural = "Cache Settings"

    def __str__(self):
        return f"Cache: {self.get_cache_backend_display()}"


class SearchLog(models.Model):
    """Track search queries for analytics"""
    query = models.CharField(max_length=200)
    results_count = models.IntegerField(default=0)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    searched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-searched_at']
        verbose_name = "Search Log"
        verbose_name_plural = "Search Logs"

    def __str__(self):
        return f"Search: {self.query}"


class BackupLog(models.Model):
    """Track backup/restore operations"""
    OPERATION_TYPES = [
        ('backup', 'Backup'),
        ('restore', 'Restore'),
        ('export', 'Export'),
        ('import', 'Import'),
    ]

    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES)
    filename = models.CharField(max_length=200, blank=True)
    file_size = models.BigIntegerField(default=0)
    success = models.BooleanField(default=True)
    message = models.TextField(blank=True)
    performed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-performed_at']
        verbose_name = "Backup Log"
        verbose_name_plural = "Backup Logs"

    def __str__(self):
        return f"{self.get_operation_type_display()} at {self.performed_at}"


class SystemLog(models.Model):
    """System logs for monitoring"""
    LOG_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('debug', 'Debug'),
    ]

    LOG_CATEGORIES = [
        ('system', 'System'),
        ('email', 'Email'),
        ('database', 'Database'),
        ('security', 'Security'),
        ('backup', 'Backup'),
        ('user', 'User'),
    ]

    level = models.CharField(max_length=20, choices=LOG_LEVELS)
    category = models.CharField(max_length=20, choices=LOG_CATEGORIES)
    message = models.TextField()
    details = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "System Log"
        verbose_name_plural = "System Logs"

    def __str__(self):
        return f"{self.get_level_display()}: {self.message[:50]}"


class AdminActionLog(models.Model):
    """Log admin actions for security"""
    ACTION_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('password_reset', 'Password Reset'),
        ('user_create', 'User Create'),
        ('user_delete', 'User Delete'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.IntegerField(null=True, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-performed_at']
        verbose_name = "Admin Action Log"
        verbose_name_plural = "Admin Action Logs"

    def __str__(self):
        return f"{self.user.username if self.user else 'System'} - {self.get_action_type_display()}"


class Language(models.Model):
    """Multilingual support - languages"""
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)
    native_name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Language"
        verbose_name_plural = "Languages"

    def __str__(self):
        return self.name


class Translation(models.Model):
    """Multilingual support - translations"""
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    key = models.CharField(max_length=200)
    value = models.TextField()
    context = models.CharField(max_length=100, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['language', 'key']
        verbose_name = "Translation"
        verbose_name_plural = "Translations"

    def __str__(self):
        return f"{self.language.code}: {self.key}"
