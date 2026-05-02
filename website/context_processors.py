from .models import SiteSettings, SocialMedia, AnimationSetting, EmailConfig, SMSConfig, HeroSection, SEOPage


def _get_page_seo(path):
    exact_match = SEOPage.objects.filter(
        is_active=True,
        match_type='exact',
        path=path
    ).first()
    if exact_match:
        return exact_match

    prefix_rules = SEOPage.objects.filter(
        is_active=True,
        match_type='prefix'
    ).order_by('priority', '-path')

    for rule in prefix_rules:
        if path.startswith(rule.path):
            return rule

    return None


def website_settings(request):
    """Add site settings to all templates"""
    try:
        # Check if SiteSettings table exists
        from django.db import connection
        table_exists = 'website_sitesettings' in connection.introspection.table_names()

        if table_exists:
            settings = SiteSettings.objects.first()
            if not settings:
                # Create default settings if none exist
                settings = SiteSettings.objects.create(
                    site_name="734 Hotel",
                    tagline="Your basecamp for good stories",
                    enable_vibe_check=True,
                    enable_guestbook=True,
                    enable_booking=True,
                    enable_map=True,
                    enable_animations=True)
        else:
            # Table doesn't exist yet (migrations not run)
            settings = None
    except Exception as e:
        print(f"Error getting site settings: {str(e)}")
        settings = None

    try:
        if settings:
            email_config = EmailConfig.objects.filter(is_active=True).first()
            sms_config = SMSConfig.objects.filter(is_active=True).first()
            hero_sections = HeroSection.objects.filter(
                is_active=True).order_by('order')
            social_media = SocialMedia.objects.filter(
                is_active=True).order_by('order')
            animation_settings = AnimationSetting.objects.filter(enabled=True)
            page_seo = _get_page_seo(request.path)
        else:
            # Return defaults if no settings exist
            email_config = None
            sms_config = None
            hero_sections = []
            social_media = []
            animation_settings = []
            page_seo = None

        return {
            'site_settings': settings,
            'social_media': social_media,
            'animation_settings': animation_settings,
            'enable_animations': settings.enable_animations if settings else True,
            'email_config': email_config,
            'sms_config': sms_config,
            'hero_sections': hero_sections,
            'page_seo': page_seo,
            'seo_title': page_seo.meta_title if page_seo else '',
            'seo_description': page_seo.meta_description if page_seo else '',
            'seo_keywords': page_seo.meta_keywords if page_seo else '',
            'seo_canonical_url': page_seo.canonical_url if page_seo else '',
            'seo_robots': page_seo.robots_content if page_seo else '',
            'seo_og_title': page_seo.og_title if page_seo else '',
            'seo_og_description': page_seo.og_description if page_seo else '',
            'seo_og_image': page_seo.og_image if page_seo and page_seo.og_image else None,
            'seo_twitter_card': page_seo.twitter_card if page_seo else '',
        }
    except Exception as e:
        print(f"Error in website_settings context processor: {str(e)}")
        return {
            'site_settings': None,
            'social_media': [],
            'animation_settings': [],
            'enable_animations': True,
            'email_config': None,
            'sms_config': None,
            'hero_sections': [],
            'page_seo': None,
            'seo_title': '',
            'seo_description': '',
            'seo_keywords': '',
            'seo_canonical_url': '',
            'seo_robots': '',
            'seo_og_title': '',
            'seo_og_description': '',
            'seo_og_image': None,
            'seo_twitter_card': '',
        }


def admin_controls(request):
    """Add admin control data to context"""
    if request.user.is_staff:
        from .models import Notification
        unread_count = Notification.objects.filter(is_read=False).count()
        recent_notifications = Notification.objects.filter(
            is_read=False).order_by('-created_at')[:5]

        return {
            'admin_unread_count': unread_count,
            'admin_recent_notifications': recent_notifications,
        }
    return {}
