from django.contrib import admin
from django import forms
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.mail import send_mail, EmailMessage
from . import views
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import json
from pathlib import Path

from .models import (
    SiteSettings, SEOPage, HeroSection, VibeCheckItem, Room, RoomImage,
    NeighborhoodPoint, GuestbookEntry, Booking,
    ContactMessage, Notification, SocialMedia,
    AnimationSetting, CustomStyle, EmailConfig, SMSConfig,
    ServiceItem, DatabaseConfig, PaymentSettings,
    PaymentProviderConfig, BookingPayment
)

# Custom Admin Site


class CustomAdminSite(admin.AdminSite):
    site_header = "734 Hotel Admin Portal"
    site_title = "734 Hotel Management"
    index_title = "Welcome to 734 Hotel Admin Portal"
    index_template = 'admin/custom_dashboard.html'

    def _build_dashboard_context(self):
        from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
        from django.db.models import Count

        # Statistics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        year_ago = today - timedelta(days=365)

        # Chart data
        monthly_bookings = Booking.objects.filter(
            created_at__gte=year_ago
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        weekly_bookings = Booking.objects.filter(
            created_at__gte=month_ago
        ).annotate(
            week=TruncWeek('created_at')
        ).values('week').annotate(
            count=Count('id')
        ).order_by('week')

        daily_bookings = Booking.objects.filter(
            created_at__gte=month_ago
        ).annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')

        top_rooms = Room.objects.annotate(
            booking_count=Count('bookings')
        ).filter(booking_count__gt=0).order_by('-booking_count')[:5]

        total_bookings = Booking.objects.count()
        confirmed_bookings = Booking.objects.filter(status='confirmed').count()
        total_contacts = ContactMessage.objects.count()
        total_inquiries = total_bookings + total_contacts
        booking_conversion_rate = (
            round((total_bookings / total_inquiries) * 100, 1)
            if total_inquiries > 0 else 0
        )

        payment_settings = PaymentSettings.objects.first()
        active_providers = PaymentProviderConfig.objects.filter(is_active=True)
        default_provider = active_providers.filter(is_default=True).first()

        ready_provider_count = 0
        for provider in active_providers:
            has_api_keys = bool(provider.secret_key)
            has_custom_template = provider.provider in [
                'momo', 'custom'] and bool(provider.checkout_url_template)
            has_paypal_keys = provider.provider == 'paypal' and bool(
                provider.public_key and provider.secret_key)

            if has_api_keys or has_custom_template or has_paypal_keys:
                ready_provider_count += 1

        online_payment_enabled = bool(
            payment_settings and payment_settings.enable_online_payment)
        payment_setup_complete = bool(
            online_payment_enabled and
            active_providers.exists() and
            default_provider and
            ready_provider_count > 0
        )

        return {
            'total_bookings': total_bookings,
            'confirmed_bookings': confirmed_bookings,
            'total_contacts': total_contacts,
            'booking_conversion_rate': booking_conversion_rate,
            'pending_bookings': Booking.objects.filter(status='pending').count(),
            'new_messages': ContactMessage.objects.filter(status='new').count(),
            'guestbook_entries': GuestbookEntry.objects.filter(is_approved=True).count(),
            'recent_bookings': Booking.objects.filter(created_at__gte=week_ago),
            'recent_messages': ContactMessage.objects.filter(created_at__gte=week_ago),
            'unread_notifications': Notification.objects.filter(is_read=False).count(),
            'site_settings': SiteSettings.objects.first(),
            'monthly_bookings': list(monthly_bookings),
            'weekly_bookings': list(weekly_bookings),
            'daily_bookings': list(daily_bookings),
            'top_rooms': top_rooms,
            'payment_settings_exists': bool(payment_settings),
            'online_payment_enabled': online_payment_enabled,
            'active_providers_count': active_providers.count(),
            'ready_provider_count': ready_provider_count,
            'default_provider_name': default_provider.display_name if default_provider else '',
            'payment_setup_complete': payment_setup_complete,
            'payment_settings_url': reverse('admin:website_paymentsettings_changelist'),
            'payment_providers_url': reverse('admin:website_paymentproviderconfig_changelist'),
            'payment_transactions_url': reverse('admin:website_bookingpayment_changelist'),
        }

    def index(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}

        extra_context.update(self._build_dashboard_context())
        extra_context['show_credential_manager'] = True
        return super().index(request, extra_context)

    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        ordering = {'website': 1, 'auth': 2}
        app_list.sort(key=lambda x: ordering.get(x['app_label'], 99))
        return app_list

    def get_urls(self):
        urls = super().get_urls()
        from django.urls import path
        custom_urls = [
            path('credential-manager/',
                 self.admin_view(views.AdminCredentialManagerView.as_view()),
                 name='credential_manager'),
        ]
        return custom_urls + urls


admin_site = CustomAdminSite(name='customadmin')

# Inline Admin Classes


class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 1
    fields = ['image', 'caption', 'order', 'is_active']
    sortable_field_name = 'order'


class SocialMediaInline(admin.TabularInline):
    model = SocialMedia
    extra = 1
    fields = ['platform', 'url', 'is_active', 'order']
    sortable_field_name = 'order'


class AnimationSettingInline(admin.TabularInline):
    model = AnimationSetting
    extra = 1
    fields = ['element', 'animation_type', 'duration', 'delay', 'enabled']


class EmailConfigInline(admin.TabularInline):
    model = EmailConfig
    extra = 1
    fields = ['email_host', 'email_port', 'email_host_user',
              'send_booking_emails', 'is_active']
    max_num = 1  # Only allow one active email config


class SMSConfigInline(admin.TabularInline):
    model = SMSConfig
    extra = 1
    fields = ['provider', 'from_number', 'send_booking_sms', 'is_active']
    max_num = 1  # Only allow one active SMS config

# Model Admins


class RoomAdminForm(forms.ModelForm):
    features_input = forms.CharField(
        required=False,
        label='Features',
        help_text='Enter one feature per line (no brackets needed).',
        widget=forms.Textarea(attrs={'rows': 5})
    )

    class Meta:
        model = Room
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_features = self.instance.features if self.instance and self.instance.features else []
        if isinstance(current_features, list):
            self.fields['features_input'].initial = '\n'.join(
                str(item) for item in current_features)
        self.fields.pop('features', None)

    def clean(self):
        cleaned_data = super().clean()
        features_raw = cleaned_data.get('features_input', '')

        parsed_features = [
            item.strip()
            for item in features_raw.replace(',', '\n').splitlines()
            if item.strip()
        ]
        cleaned_data['features'] = parsed_features
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.features = self.cleaned_data.get('features', [])
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ServiceItemAdminForm(forms.ModelForm):
    ICON_PRESET_CHOICES = [
        ('concierge', 'Concierge Bell'),
        ('wifi', 'Wi-Fi'),
        ('utensils', 'Restaurant/Food'),
        ('car', 'Transport'),
        ('spa', 'Spa/Wellness'),
        ('swimmer', 'Pool'),
        ('dumbbell', 'Gym/Fitness'),
        ('shield', 'Security'),
        ('broom', 'Cleaning'),
        ('coffee', 'Coffee/Breakfast'),
        ('custom', 'Custom Icon Class'),
    ]

    ICON_CLASS_MAP = {
        'concierge': 'fas fa-concierge-bell',
        'wifi': 'fas fa-wifi',
        'utensils': 'fas fa-utensils',
        'car': 'fas fa-car',
        'spa': 'fas fa-spa',
        'swimmer': 'fas fa-swimmer',
        'dumbbell': 'fas fa-dumbbell',
        'shield': 'fas fa-shield-alt',
        'broom': 'fas fa-broom',
        'coffee': 'fas fa-coffee',
    }

    icon_preset = forms.ChoiceField(
        choices=ICON_PRESET_CHOICES,
        required=True,
        label='Icon',
        help_text='Choose an icon from the list.'
    )
    custom_icon_class = forms.CharField(
        required=False,
        label='Custom Icon Class',
        help_text='Only used when Icon = Custom Icon Class. Example: fas fa-star'
    )

    class Meta:
        model = ServiceItem
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_icon = self.instance.icon_class if self.instance and self.instance.icon_class else ''

        reverse_map = {value: key for key,
                       value in self.ICON_CLASS_MAP.items()}
        if current_icon in reverse_map:
            self.fields['icon_preset'].initial = reverse_map[current_icon]
            self.fields['custom_icon_class'].initial = ''
        else:
            self.fields['icon_preset'].initial = 'custom'
            self.fields['custom_icon_class'].initial = current_icon

        self.fields.pop('icon_class', None)

    def clean(self):
        cleaned_data = super().clean()
        icon_preset = cleaned_data.get('icon_preset')
        custom_icon_class = (cleaned_data.get(
            'custom_icon_class') or '').strip()

        if icon_preset == 'custom':
            cleaned_data['icon_class'] = custom_icon_class or 'fas fa-concierge-bell'
        else:
            cleaned_data['icon_class'] = self.ICON_CLASS_MAP.get(
                icon_preset, 'fas fa-concierge-bell')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.icon_class = self.cleaned_data.get(
            'icon_class', 'fas fa-concierge-bell')
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(SiteSettings, site=admin_site)
class SiteSettingsAdmin(admin.ModelAdmin):
    inlines = [SocialMediaInline, AnimationSettingInline,
               EmailConfigInline, SMSConfigInline]
    fieldsets = (
        ('Basic Information', {
            'description': 'Set your hotel name, tagline, description, and brand images.',
            'fields': ('site_name', 'tagline', 'description', 'logo', 'favicon')
        }),
        ('SEO & Sharing', {
            'description': 'Control search engine text and social media preview details.',
            'fields': ('meta_description', 'meta_keywords', 'og_image')
        }),
        ('Color Theme', {
            'description': 'Choose the main colors used across the website.',
            'fields': ('primary_color', 'secondary_color', 'accent_color',
                       'background_color', 'text_color')
        }),
        ('Typography', {
            'description': 'Choose the font style for normal text and headings.',
            'fields': ('font_family', 'heading_font')
        }),
        ('Animations & Effects', {
            'description': 'Enable and tune animation speed, motion strength, and scroll feel.',
            'fields': ('enable_animations', 'animation_speed', 'motion_intensity', 'scroll_smoothness')
        }),
        ('Feature Management', {
            'description': 'Turn key website sections on or off without touching code.',
            'fields': ('enable_vibe_check', 'enable_guestbook',
                       'enable_booking', 'enable_map', 'enable_datepicker')
        }),
        ('Layout', {
            'description': 'Select the visual layout style for the website.',
            'fields': ('layout_style',)
        }),
        ('Advanced Custom CSS (Optional)', {
            'description': 'Only for advanced styling changes. Leave empty for normal use.',
            'fields': ('custom_css',),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        platform_icon_map = {
            'facebook': 'fab fa-facebook-f',
            'instagram': 'fab fa-instagram',
            'twitter': 'fab fa-twitter',
            'tripadvisor': 'fab fa-tripadvisor',
            'youtube': 'fab fa-youtube',
            'linkedin': 'fab fa-linkedin-in',
            'pinterest': 'fab fa-pinterest-p',
            'tiktok': 'fab fa-tiktok',
        }

        for instance in instances:
            if isinstance(instance, SocialMedia):
                instance.icon_class = platform_icon_map.get(
                    instance.platform, instance.icon_class or '')
            instance.save()

        for obj in formset.deleted_objects:
            obj.delete()

        formset.save_m2m()


@admin.register(HeroSection, site=admin_site)
class HeroSectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'order']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
    fieldsets = (
        ('Content', {
            'fields': ('title', 'subtitle', 'background_image')
        }),
        ('Button Settings', {
            'fields': ('button_text', 'button_link')
        }),
        ('Display Settings', {
            'fields': ('overlay_opacity', 'is_active', 'order')
        }),
        ('Animations', {
            'fields': ('enable_title_animation', 'title_animation_type',
                       'enable_subtitle_animation', 'subtitle_animation_delay')
        }),
    )


@admin.register(SEOPage, site=admin_site)
class SEOPageAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'path', 'match_type', 'priority', 'is_active', 'updated_at'
    ]
    list_editable = ['priority', 'is_active']
    list_filter = ['match_type', 'is_active', 'robots_index', 'robots_follow']
    search_fields = ['name', 'path', 'meta_title', 'meta_description']
    ordering = ['priority', 'path']

    fieldsets = (
        ('Target URL Rule', {
            'description': 'Create SEO rules per page path. Use exact for one page, prefix for all child URLs.',
            'fields': ('name', 'path', 'match_type', 'priority', 'is_active')
        }),
        ('Search Snippet (Google)', {
            'description': 'Main SEO text shown in search results.',
            'fields': ('meta_title', 'meta_description', 'meta_keywords', 'canonical_url')
        }),
        ('Robots', {
            'description': 'Control indexing and link-follow behavior.',
            'fields': ('robots_index', 'robots_follow')
        }),
        ('Social Sharing (Open Graph / Twitter)', {
            'description': 'Controls preview title, description and image on social apps.',
            'fields': ('og_title', 'og_description', 'og_image', 'twitter_card')
        }),
    )


@admin.register(VibeCheckItem, site=admin_site)
class VibeCheckItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'image', 'description')
        }),
        ('Audio Experience', {
            'fields': ('audio_file', 'audio_url')
        }),
        ('Guest Testimonial', {
            'fields': ('guest_note', 'guest_name', 'guest_country')
        }),
        ('Display Settings', {
            'fields': ('is_active', 'order')
        }),
    )


@admin.register(Room, site=admin_site)
class RoomAdmin(admin.ModelAdmin):
    form = RoomAdminForm
    inlines = [RoomImageInline]
    list_display = ['name', 'room_type',
                    'price_per_night', 'is_available', 'is_featured']
    list_editable = ['is_available', 'is_featured']
    list_filter = ['room_type', 'is_available', 'is_featured']
    search_fields = ['name', 'description']
    fieldsets = (
        ('Room Information', {
            'fields': ('name', 'room_type', 'description', 'price_per_night')
        }),
        ('Capacity', {
            'fields': ('capacity', 'available_beds')
        }),
        ('Visuals', {
            'fields': ('main_image', 'color_accent')
        }),
        ('Features', {
            'fields': ('features_input',)
        }),
        ('Display Settings', {
            'fields': ('is_featured', 'is_available', 'order', 'hover_effect')
        }),
    )


@admin.register(NeighborhoodPoint, site=admin_site)
class NeighborhoodPointAdmin(admin.ModelAdmin):
    list_display = ['title', 'point_type', 'is_active']
    list_filter = ['point_type', 'is_active']
    search_fields = ['title', 'description']
    fieldsets = (
        ('Location Information', {
            'fields': ('title', 'description', 'point_type')
        }),
        ('Coordinates', {
            'fields': ('latitude', 'longitude')
        }),
        ('Display Settings', {
            'fields': ('icon', 'color', 'is_active')
        }),
    )


@admin.register(GuestbookEntry, site=admin_site)
class GuestbookEntryAdmin(admin.ModelAdmin):
    list_display = ['name', 'hometown', 'is_approved', 'created_at']
    list_editable = ['is_approved']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['name', 'hometown', 'message']
    actions = ['approve_entries', 'delete_unapproved']

    fieldsets = (
        ('Entry Details', {
            'fields': ('name', 'hometown', 'message', 'color')
        }),
        ('Moderation', {
            'fields': ('is_approved', 'ip_address')
        }),
    )

    def approve_entries(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} entries approved.')
    approve_entries.short_description = "Approve selected entries"

    def delete_unapproved(self, request, queryset):
        deleted, _ = queryset.filter(is_approved=False).delete()
        self.message_user(request, f'{deleted} unapproved entries deleted.')
    delete_unapproved.short_description = "Delete unapproved entries"


@admin.register(Booking, site=admin_site)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'guest_name', 'room',
                    'check_in', 'check_out', 'status', 'created_at']
    list_filter = ['status', 'check_in', 'check_out', 'room']
    search_fields = ['guest_name', 'guest_email', 'guest_phone']
    readonly_fields = ['created_at', 'updated_at',
                       'total_price', 'email_replies_display',
                       'guest_access_token', 'manage_booking_link',
                       'cancelled_at']
    actions = ['confirm_bookings',
               'cancel_bookings', 'send_confirmation_email']

    fieldsets = (
        ('Guest Information', {
            'fields': ('guest_name', 'guest_email', 'guest_phone', 'guest_country')
        }),
        ('Booking Details', {
            'fields': ('room', 'check_in', 'check_out', 'number_of_guests', 'special_requests')
        }),
        ('Status & Pricing', {
            'fields': ('status', 'total_price')
        }),
        ('Admin Notes', {
            'fields': ('admin_notes', 'email_sent', 'email_replies_display')
        }),
        ('Guest Self-Service', {
            'fields': ('guest_access_token', 'manage_booking_link', 'cancellation_reason', 'cancelled_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def manage_booking_link(self, obj):
        if not obj.guest_access_token:
            return "Not available"
        path = reverse('manage_booking', kwargs={
                       'token': obj.guest_access_token})
        return format_html('<a href="{}" target="_blank">Open guest manage page</a>', path)
    manage_booking_link.short_description = "Guest Manage Link"

    def response_change(self, request, obj):
        if "_reply" in request.POST:
            reply_message = request.POST.get('admin_reply', '')
            if reply_message:
                subject = f"Re: Your booking at 734 Hotel (Booking #{obj.id})"
                message = f"Dear {obj.guest_name},\n\n{reply_message}\n\nBest regards,\n734 Hotel Team"

                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[obj.guest_email],
                    fail_silently=False,
                )

                if not obj.email_replies:
                    obj.email_replies = []
                obj.email_replies.append({
                    'message': reply_message,
                    'sent_at': timezone.now().isoformat(),
                    'sent_by': request.user.username
                })
                obj.save()

                messages.success(request, "Reply sent successfully!")

            return HttpResponseRedirect(request.path)

        return super().response_change(request, obj)

    def email_replies_display(self, obj):
        if not obj.email_replies:
            return "No replies yet"

        lines = []
        for reply in reversed(obj.email_replies):
            sent_by = reply.get('sent_by', 'Unknown')
            sent_at = reply.get('sent_at', '')
            message = reply.get('message', '')
            lines.append(f"{sent_at} | {sent_by}\n{message}")

        return "\n\n".join(lines)
    email_replies_display.short_description = "Reply History"

    def confirm_bookings(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, f'{queryset.count()} bookings confirmed.')
    confirm_bookings.short_description = "Confirm selected bookings"

    def cancel_bookings(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, f'{queryset.count()} bookings cancelled.')
    cancel_bookings.short_description = "Cancel selected bookings"

    def send_confirmation_email(self, request, queryset):
        for booking in queryset:
            if not booking.email_sent:
                subject = f"Booking Confirmation - 734 Hotel"
                html_message = render_to_string('email/booking_confirmation.html', {
                    'booking': booking
                })

                email = EmailMessage(
                    subject=subject,
                    body=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[booking.guest_email],
                )
                email.content_subtype = "html"
                email.send()

                booking.email_sent = True
                booking.save()

        self.message_user(
            request, f'Confirmation emails sent for {queryset.count()} bookings.')
    send_confirmation_email.short_description = "Send confirmation emails"


@admin.register(ContactMessage, site=admin_site)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['created_at', 'ip_address',
                       'admin_responded_by', 'admin_responded_at']
    actions = ['mark_as_replied', 'send_reply_email']
    change_form_template = 'admin/website/contactmessage/change_form.html'

    fieldsets = (
        ('Message Details', {
            'fields': ('name', 'email', 'subject', 'message')
        }),
        ('Response', {
            'fields': ('status', 'admin_response', 'admin_responded_by', 'admin_responded_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'ip_address')
        }),
    )

    def _append_reply_history(self, obj, reply_text, username):
        if not obj.reply_history:
            obj.reply_history = []
        obj.reply_history.append({
            'message': reply_text,
            'sent_at': timezone.now().isoformat(),
            'sent_by': username,
        })

    def response_change(self, request, obj):
        if "_reply" in request.POST:
            reply_message = request.POST.get('admin_reply', '').strip()
            if not reply_message:
                messages.error(
                    request, "Please type a reply message before sending.")
                return HttpResponseRedirect(request.path)

            try:
                send_mail(
                    subject=f"Re: {obj.subject}",
                    message=f"Dear {obj.name},\n\n{reply_message}\n\nBest regards,\n734 Hotel Team",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[obj.email],
                    fail_silently=False,
                )

                obj.status = 'replied'
                obj.admin_response = reply_message
                obj.admin_responded_by = request.user
                obj.admin_responded_at = timezone.now()
                self._append_reply_history(
                    obj, reply_message, request.user.username)
                obj.save(update_fields=[
                         'status', 'admin_response', 'admin_responded_by', 'admin_responded_at', 'reply_history'])

                messages.success(request, "Reply sent successfully.")
            except Exception as exc:
                messages.error(request, f"Reply failed: {exc}")

            return HttpResponseRedirect(request.path)

        return super().response_change(request, obj)

    def save_model(self, request, obj, form, change):
        if 'admin_response' in form.changed_data and form.cleaned_data['admin_response']:
            obj.status = 'replied'
            obj.admin_responded_by = request.user
            obj.admin_responded_at = timezone.now()

            subject = f"Re: {obj.subject}"
            message = f"Dear {obj.name},\n\n{form.cleaned_data['admin_response']}\n\nBest regards,\n734 Hotel Team"

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[obj.email],
                fail_silently=False,
            )

            self._append_reply_history(
                obj, form.cleaned_data['admin_response'], request.user.username)

        super().save_model(request, obj, form, change)

    def mark_as_replied(self, request, queryset):
        queryset.update(status='replied')
        self.message_user(
            request, f'{queryset.count()} messages marked as replied.')
    mark_as_replied.short_description = "Mark as replied"

    def send_reply_email(self, request, queryset):
        sent_count = 0
        for message_obj in queryset:
            if not message_obj.admin_response:
                continue
            try:
                send_mail(
                    subject=f"Re: {message_obj.subject}",
                    message=f"Dear {message_obj.name},\n\n{message_obj.admin_response}\n\nBest regards,\n734 Hotel Team",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[message_obj.email],
                    fail_silently=False,
                )
                message_obj.status = 'replied'
                message_obj.admin_responded_by = request.user
                message_obj.admin_responded_at = timezone.now()
                self._append_reply_history(
                    message_obj, message_obj.admin_response, request.user.username)
                message_obj.save(
                    update_fields=['status', 'admin_responded_by', 'admin_responded_at', 'reply_history'])
                sent_count += 1
            except Exception:
                continue

        self.message_user(request, f"Sent {sent_count} reply email(s).")
    send_reply_email.short_description = "Send reply email using saved response"


@admin.register(Notification, site=admin_site)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    readonly_fields = ['created_at', 'read_at', 'read_by']
    actions = ['mark_as_read', 'mark_as_unread']

    fieldsets = (
        ('Notification Details', {
            'fields': ('notification_type', 'title', 'message')
        }),
        ('Related Object', {
            'fields': ('related_object_id', 'related_object_type')
        }),
        ('Read Status', {
            'fields': ('is_read', 'read_by', 'read_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True, read_by=request.user,
                        read_at=timezone.now())
        self.message_user(
            request, f'{queryset.count()} notifications marked as read.')
    mark_as_read.short_description = "Mark as read"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_by=None, read_at=None)
        self.message_user(
            request, f'{queryset.count()} notifications marked as unread.')
    mark_as_unread.short_description = "Mark as unread"


@admin.register(AnimationSetting, site=admin_site)
class AnimationSettingAdmin(admin.ModelAdmin):
    list_display = ['element', 'animation_type',
                    'duration', 'delay', 'enabled']
    list_editable = ['enabled', 'duration', 'delay']
    list_filter = ['enabled', 'animation_type']
    search_fields = ['element']


@admin.register(CustomStyle, site=admin_site)
class CustomStyleAdmin(admin.ModelAdmin):
    list_display = ['name', 'css_class', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name', 'css_class']


@admin.register(EmailConfig, site=admin_site)
class EmailConfigAdmin(admin.ModelAdmin):
    list_display = ['email_host', 'email_port',
                    'default_from_email', 'is_active']
    list_editable = ['is_active']
    fieldsets = (
        ('SMTP Settings', {
            'fields': ('email_backend', 'email_host', 'email_port', 'email_protocol',
                       'email_use_tls', 'email_use_ssl')
        }),
        ('Credentials', {
            'fields': ('email_host_user', 'email_host_password', 'default_from_email')
        }),
        ('Templates', {
            'fields': ('booking_confirmation_template', 'booking_cancellation_template',
                       'contact_reply_template')
        }),
        ('Settings', {
            'fields': ('send_booking_emails', 'send_contact_emails', 'send_newsletter')
        }),
        ('Test', {
            'fields': ('test_email_address',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(SMSConfig, site=admin_site)
class SMSConfigAdmin(admin.ModelAdmin):
    list_display = ['provider', 'from_number', 'send_booking_sms', 'is_active']
    list_editable = ['is_active']
    fieldsets = (
        ('Provider Settings', {
            'fields': ('provider', 'api_url')
        }),
        ('Credentials', {
            'fields': ('api_key', 'api_secret', 'account_sid', 'auth_token', 'from_number')
        }),
        ('Templates', {
            'fields': ('booking_sms_template', 'reminder_sms_template')
        }),
        ('Settings', {
            'fields': ('send_booking_sms', 'send_reminder_sms', 'send_promotional_sms')
        }),
        ('Test', {
            'fields': ('test_phone_number',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(ServiceItem, site=admin_site)
class ServiceItemAdmin(admin.ModelAdmin):
    form = ServiceItemAdminForm
    list_display = ['title', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['title', 'description']
    list_filter = ['is_active']
    fieldsets = (
        ('Service Information', {
            'fields': ('title', 'description')
        }),
        ('Icon', {
            'fields': ('icon_preset', 'custom_icon_class')
        }),
        ('Display', {
            'fields': ('is_active', 'order')
        }),
    )


@admin.register(DatabaseConfig, site=admin_site)
class DatabaseConfigAdmin(admin.ModelAdmin):
    list_display = ['engine', 'is_active', 'updated_at']
    list_editable = ['is_active']
    readonly_fields = ['updated_at']
    fieldsets = (
        ('Database Type', {
            'fields': ('engine', 'is_active')
        }),
        ('SQLite', {
            'fields': ('sqlite_name',)
        }),
        ('PostgreSQL', {
            'fields': ('postgres_name', 'postgres_user', 'postgres_password', 'postgres_host', 'postgres_port')
        }),
        ('Metadata', {
            'fields': ('updated_at',)
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.is_active:
            DatabaseConfig.objects.exclude(pk=obj.pk).update(is_active=False)

        project_root = Path(__file__).resolve().parent.parent
        config_path = project_root / 'db_config.json'

        payload = {
            'engine': obj.engine,
            'sqlite_name': obj.sqlite_name,
            'postgres_name': obj.postgres_name,
            'postgres_user': obj.postgres_user,
            'postgres_password': obj.postgres_password,
            'postgres_host': obj.postgres_host,
            'postgres_port': obj.postgres_port,
            'is_active': obj.is_active,
        }

        with open(config_path, 'w', encoding='utf-8') as config_file:
            json.dump(payload, config_file, indent=2)

        messages.info(
            request, "Database configuration saved. Restart the server to apply changes.")


@admin.register(PaymentSettings, site=admin_site)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ['enable_online_payment', 'auto_confirm_booking_on_payment',
                    'allow_guest_changes_after_payment', 'default_currency', 'updated_at']
    readonly_fields = ['updated_at']
    fieldsets = (
        ('Payment Controls', {
            'fields': ('enable_online_payment', 'default_currency')
        }),
        ('Booking Behavior', {
            'fields': ('auto_confirm_booking_on_payment', 'allow_guest_changes_after_payment')
        }),
        ('Redirects', {
            'fields': ('success_redirect_path', 'cancel_redirect_path')
        }),
        ('Metadata', {
            'fields': ('updated_at',)
        }),
    )

    def has_add_permission(self, request):
        return not PaymentSettings.objects.exists()


@admin.register(PaymentProviderConfig, site=admin_site)
class PaymentProviderConfigAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'provider',
                    'is_active', 'is_default', 'priority']
    list_editable = ['is_active', 'is_default', 'priority']
    list_filter = ['provider', 'is_active', 'is_default']
    search_fields = ['display_name', 'provider']
    actions = ['create_default_provider_presets']
    fieldsets = (
        ('Provider', {
            'fields': ('display_name', 'provider', 'is_active', 'is_default', 'priority')
        }),
        ('Credentials', {
            'fields': ('public_key', 'secret_key', 'webhook_secret')
        }),
        ('Endpoints', {
            'fields': ('api_base_url', 'callback_url', 'checkout_url_template')
        }),
        ('Advanced', {
            'fields': ('extra_config',)
        }),
    )

    def create_default_provider_presets(self, request, queryset):
        presets = [
            {
                'provider': 'stripe',
                'display_name': 'Stripe Card Payments',
                'priority': 10,
                'api_base_url': 'https://api.stripe.com/v1/checkout/sessions',
                'callback_url': '',
                'checkout_url_template': '',
                'extra_config': {
                    'mode': 'test',
                    'hint': 'Set public_key and secret_key from Stripe dashboard.'
                },
            },
            {
                'provider': 'paystack',
                'display_name': 'Paystack',
                'priority': 20,
                'api_base_url': 'https://api.paystack.co/transaction/initialize',
                'callback_url': '',
                'checkout_url_template': '',
                'extra_config': {
                    'mode': 'test',
                    'hint': 'Set secret_key from Paystack dashboard.'
                },
            },
            {
                'provider': 'paypal',
                'display_name': 'PayPal Checkout',
                'priority': 30,
                'api_base_url': 'https://api-m.sandbox.paypal.com',
                'callback_url': '',
                'checkout_url_template': '',
                'extra_config': {
                    'mode': 'sandbox',
                    'hint': 'Set public_key=client_id and secret_key from PayPal app.'
                },
            },
            {
                'provider': 'momo',
                'display_name': 'Mobile Money (Custom)',
                'priority': 40,
                'api_base_url': '',
                'callback_url': '',
                'checkout_url_template': 'https://your-momo-provider.example/pay?amount={amount}&currency={currency}&reference={reference}&email={email}&callback={callback_url}',
                'extra_config': {
                    'hint': 'Replace checkout_url_template with your provider URL format.'
                },
            },
        ]

        created_count = 0
        for preset in presets:
            _, created = PaymentProviderConfig.objects.get_or_create(
                provider=preset['provider'],
                display_name=preset['display_name'],
                defaults={
                    'priority': preset['priority'],
                    'api_base_url': preset['api_base_url'],
                    'callback_url': preset['callback_url'],
                    'checkout_url_template': preset['checkout_url_template'],
                    'extra_config': preset['extra_config'],
                    'is_active': False,
                    'is_default': preset['provider'] == 'stripe',
                }
            )
            if created:
                created_count += 1

        self.message_user(
            request,
            f'{created_count} payment provider preset(s) created. Open each preset, add your real credentials, then activate the one(s) you want.'
        )

    create_default_provider_presets.short_description = 'Create default payment provider presets'


@admin.register(BookingPayment, site=admin_site)
class BookingPaymentAdmin(admin.ModelAdmin):
    list_display = ['reference', 'booking', 'provider',
                    'amount', 'currency', 'status', 'created_at']
    list_filter = ['status', 'currency', 'provider', 'created_at']
    search_fields = ['reference',
                     'booking__guest_name', 'booking__guest_email']
    readonly_fields = ['reference', 'created_at', 'updated_at', 'paid_at',
                       'checkout_url', 'external_reference', 'provider_response']
    fieldsets = (
        ('Payment', {
            'fields': ('booking', 'provider', 'amount', 'currency', 'status')
        }),
        ('References', {
            'fields': ('reference', 'external_reference', 'checkout_url')
        }),
        ('Provider Data', {
            'fields': ('provider_response', 'notes')
        }),
        ('Timestamps', {
            'fields': ('paid_at', 'created_at', 'updated_at')
        }),
    )

# Custom User Admin


class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name',
                    'last_name', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_active', 'groups']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    # Add actions for admin
    actions = ['reset_password']

    def reset_password(self, request, queryset):
        for user in queryset:
            # Generate a random password
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits
            new_password = ''.join(secrets.choice(alphabet) for _ in range(12))

            # Set the new password
            user.set_password(new_password)
            user.save()

            # Send email with new password (optional)
            if user.email:
                try:
                    send_mail(
                        subject='734 Hotel - Password Reset',
                        message=f'Your password has been reset. New password: {new_password}\n\nPlease change it after logging in.',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
                except:
                    pass

        self.message_user(
            request, f'Passwords reset for {queryset.count()} users.')
    reset_password.short_description = "Reset passwords for selected users"


# Unregister Group
admin.site.unregister(Group)

# Register User with custom admin
admin_site.register(User, CustomUserAdmin)

# Custom Dashboard


def admin_dashboard(request):
    from django.shortcuts import render
    from django.contrib.auth.decorators import login_required
    from django.utils.decorators import method_decorator
    from django.views.generic import TemplateView

    @method_decorator(login_required)
    class AdminDashboardView(TemplateView):
        template_name = 'admin/custom_dashboard.html'

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)

            # Statistics
            today = timezone.now().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            year_ago = today - timedelta(days=365)

            # Chart data for bookings over time
            from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
            from django.db.models import Count

            # Monthly bookings for the last 12 months
            monthly_bookings = Booking.objects.filter(
                created_at__gte=year_ago
            ).annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')

            # Weekly bookings for the last 12 weeks
            weekly_bookings = Booking.objects.filter(
                created_at__gte=month_ago
            ).annotate(
                week=TruncWeek('created_at')
            ).values('week').annotate(
                count=Count('id')
            ).order_by('week')

            # Daily bookings for the last 30 days
            daily_bookings = Booking.objects.filter(
                created_at__gte=month_ago
            ).annotate(
                day=TruncDay('created_at')
            ).values('day').annotate(
                count=Count('id')
            ).order_by('day')

            context.update({
                'total_bookings': Booking.objects.count(),
                'pending_bookings': Booking.objects.filter(status='pending').count(),
                'new_messages': ContactMessage.objects.filter(status='new').count(),
                'guestbook_entries': GuestbookEntry.objects.filter(is_approved=True).count(),
                'recent_bookings': Booking.objects.filter(created_at__gte=week_ago),
                'recent_messages': ContactMessage.objects.filter(created_at__gte=week_ago),
                'unread_notifications': Notification.objects.filter(is_read=False).count(),
                'site_settings': SiteSettings.objects.first(),
                'monthly_bookings': list(monthly_bookings),
                'weekly_bookings': list(weekly_bookings),
                'daily_bookings': list(daily_bookings),
            })

            return context

    return AdminDashboardView.as_view()(request)
