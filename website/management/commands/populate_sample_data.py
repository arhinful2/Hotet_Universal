from django.core.management.base import BaseCommand
from website.models import (
    SiteSettings, HeroSection, VibeCheckItem, Room, RoomImage,
    NeighborhoodPoint, GuestbookEntry, SocialMedia, AnimationSetting
)


class Command(BaseCommand):
    help = 'Populate the database with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Populating sample data...')

        # Create SiteSettings if not exists
        settings, created = SiteSettings.objects.get_or_create(
            defaults={
                'site_name': '734 Hotel',
                'tagline': 'Your basecamp for good stories',
                'primary_color': '#E76F51',
                'secondary_color': '#2A9D8F',
                'accent_color': '#E9C46A',
                'enable_vibe_check': True,
                'enable_guestbook': True,
                'enable_booking': True,
                'enable_map': True,
                'enable_animations': True,
            }
        )
        if created:
            self.stdout.write('Created SiteSettings')

        # Create Hero Sections
        if not HeroSection.objects.exists():
            HeroSection.objects.create(
                title='Welcome to 734 Hotel',
                subtitle='Your basecamp for good stories',
                background_image='hero/hero1.jpg',
                is_active=True,
                order=1
            )
            HeroSection.objects.create(
                title='Experience Accra',
                subtitle='Discover the vibrant culture and warm hospitality',
                background_image='hero/hero2.jpg',
                is_active=True,
                order=2
            )
            self.stdout.write('Created Hero Sections')

        # Create Vibe Check Items
        if not VibeCheckItem.objects.exists():
            VibeCheckItem.objects.create(
                title='The Cozy Bunk',
                description='Comfortable bunks with privacy curtains',
                image='vibe_check/bunk.jpg',
                audio='audio/bunk_vibe.mp3',
                guest_note='The bunks are so comfortable, I slept like a baby!',
                guest_name='Sarah M.',
                is_active=True,
                order=1
            )
            VibeCheckItem.objects.create(
                title='Shared Kitchen',
                description='Cook together and share meals',
                image='vibe_check/kitchen.jpg',
                audio='audio/kitchen_vibe.mp3',
                guest_note='Cooking with other travelers was the highlight!',
                guest_name='Carlos R.',
                is_active=True,
                order=2
            )
            VibeCheckItem.objects.create(
                title='Rooftop Sunset',
                description='Watch the sunset from our rooftop',
                image='vibe_check/rooftop.jpg',
                audio='audio/rooftop_vibe.mp3',
                guest_note='The rooftop views are absolutely stunning!',
                guest_name='Aisha K.',
                is_active=True,
                order=3
            )
            self.stdout.write('Created Vibe Check Items')

        # Create Rooms
        if not Room.objects.exists():
            room1 = Room.objects.create(
                name='Mixed Dorm',
                room_type='dorm',
                description='Comfortable mixed dormitory with 8 bunks',
                price_per_night=25,
                capacity=8,
                available_beds=8,
                is_available=True,
                order=1
            )
            room2 = Room.objects.create(
                name='Private Double',
                room_type='private',
                description='Private room with double bed',
                price_per_night=60,
                capacity=2,
                available_beds=2,
                is_available=True,
                order=2
            )
            self.stdout.write('Created Rooms')

        # Create Neighborhood Points
        if not NeighborhoodPoint.objects.exists():
            NeighborhoodPoint.objects.create(
                title='Midnight Tacos',
                description='Best late-night tacos in the city. Open until 3 AM.',
                latitude=5.6037,
                longitude=-0.1870,
                point_type='food',
                color='#E76F51',
                is_active=True
            )
            NeighborhoodPoint.objects.create(
                title='Hidden Jazz Bar',
                description='Intimate jazz club with live music every night.',
                latitude=5.6038,
                longitude=-0.1871,
                point_type='entertainment',
                color='#2A9D8F',
                is_active=True
            )
            NeighborhoodPoint.objects.create(
                title='Brew & Work Cafe',
                description='Artisan coffee with fast free WiFi. Perfect for digital nomads.',
                latitude=5.6039,
                longitude=-0.1872,
                point_type='food',
                color='#E9C46A',
                is_active=True
            )
            self.stdout.write('Created Neighborhood Points')

        # Create Guestbook Entries
        if not GuestbookEntry.objects.exists():
            GuestbookEntry.objects.create(
                name='Sarah M.',
                hometown='Toronto, Canada',
                message='The best hostel experience I\'ve ever had! Met amazing people and the staff felt like family.',
                color='#E9C46A',
                is_approved=True
            )
            GuestbookEntry.objects.create(
                name='Carlos R.',
                hometown='Barcelona, Spain',
                message='The rooftop sunset views are incredible! Perfect place to unwind after a day of exploring.',
                color='#2A9D8F',
                is_approved=True
            )
            GuestbookEntry.objects.create(
                name='Aisha K.',
                hometown='Nairobi, Kenya',
                message='The family dinners were the highlight of my stay. Such a warm, welcoming community!',
                color='#E76F51',
                is_approved=True
            )
            self.stdout.write('Created Guestbook Entries')

        # Create Social Media
        if not SocialMedia.objects.exists():
            SocialMedia.objects.create(
                platform='facebook',
                url='https://facebook.com/734hotel',
                icon_class='fab fa-facebook-f',
                is_active=True,
                order=1
            )
            SocialMedia.objects.create(
                platform='instagram',
                url='https://instagram.com/734hotel',
                icon_class='fab fa-instagram',
                is_active=True,
                order=2
            )
            self.stdout.write('Created Social Media')

        # Create Animation Settings
        if not AnimationSetting.objects.exists():
            AnimationSetting.objects.create(
                element='hero-title',
                animation_type='fade',
                duration=1000,
                delay=200,
                enabled=True
            )
            AnimationSetting.objects.create(
                element='rooms-section',
                animation_type='slide',
                duration=800,
                delay=100,
                enabled=True
            )
            self.stdout.write('Created Animation Settings')

        self.stdout.write(self.style.SUCCESS(
            'Sample data populated successfully!'))
