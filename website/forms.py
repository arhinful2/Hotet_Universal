from django import forms
from django.core.validators import EmailValidator, MinValueValidator, ValidationError
from django.utils import timezone
from datetime import date
from .models import (
    Booking, ContactMessage, GuestbookEntry,
    EmailConfig, SMSConfig, DatabaseConfig
)


class NonRequiredForm(forms.Form):
    """Base form with no required fields"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False


class BookingForm(forms.ModelForm):
    check_in = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}),
        help_text="Select your check-in date"
    )

    check_out = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}),
        help_text="Select your check-out date"
    )

    class Meta:
        model = Booking
        fields = [
            'guest_name', 'guest_email', 'guest_phone',
            'guest_country', 'room', 'check_in', 'check_out',
            'number_of_guests', 'special_requests'
        ]
        widgets = {
            'guest_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your full name',
                'required': True
            }),
            'guest_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.email@example.com',
                'required': True
            }),
            'guest_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1234567890'
            }),
            'guest_country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your country'
            }),
            'room': forms.HiddenInput(attrs={'class': 'form-control'}),
            'number_of_guests': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10,
                'value': 1
            }),
            'special_requests': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Any special requests or requirements...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make only required fields actually required
        self.fields['guest_name'].required = True
        self.fields['guest_email'].required = True
        self.fields['room'].required = True
        self.fields['check_in'].required = True
        self.fields['check_out'].required = True
        self.fields['number_of_guests'].required = True

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')
        number_of_guests = cleaned_data.get('number_of_guests')
        room = cleaned_data.get('room')

        if check_in and check_out:
            if check_in < date.today():
                raise forms.ValidationError(
                    "Check-in date cannot be in the past.")
            if check_out <= check_in:
                raise forms.ValidationError(
                    "Check-out date must be after check-in date.")

        if room and number_of_guests:
            if number_of_guests > room.capacity:
                raise forms.ValidationError(
                    f"This room can only accommodate {room.capacity} guests. "
                    f"You selected {number_of_guests} guests."
                )
            if number_of_guests > room.available_beds:
                raise forms.ValidationError(
                    f"Only {room.available_beds} beds are available in this room."
                )

        if room and check_in and check_out:
            overlapping_bookings = Booking.objects.filter(
                room=room,
                status__in=['pending', 'confirmed'],
                check_in__lt=check_out,
                check_out__gt=check_in
            )

            if self.instance and self.instance.pk:
                overlapping_bookings = overlapping_bookings.exclude(
                    pk=self.instance.pk)

            if overlapping_bookings.exists():
                raise forms.ValidationError(
                    "Selected dates are no longer available for this room. "
                    "Please choose different dates or another room."
                )

        return cleaned_data


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your name',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.email@example.com',
                'required': True
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Subject of your message',
                'required': True
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Your message...',
                'required': True
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields required
        for field in ['name', 'email', 'subject', 'message']:
            self.fields[field].required = True


class GuestbookForm(forms.ModelForm):
    class Meta:
        model = GuestbookEntry
        fields = ['name', 'hometown', 'message', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your name',
                'required': True
            }),
            'hometown': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Where are you from?',
                'required': True
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Share your experience...',
                'required': True
            }),
            'color': forms.HiddenInput(attrs={
                'value': '#E9C46A'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make name, hometown, and message required
        for field in ['name', 'hometown', 'message']:
            self.fields[field].required = True
        # Make color not required
        self.fields['color'].required = False
        self.fields['color'].initial = '#E9C46A'


class AdminReplyForm(forms.Form):
    """Form for admin to reply to messages"""
    reply_message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Type your reply here...',
            'required': True
        }),
        required=True
    )


class GuestBookingManageForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['check_in', 'check_out',
                  'number_of_guests', 'special_requests']
        widgets = {
            'check_in': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'check_out': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'number_of_guests': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'special_requests': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')
        number_of_guests = cleaned_data.get('number_of_guests')

        if check_in and check_out:
            if check_in < date.today():
                raise forms.ValidationError(
                    "Check-in date cannot be in the past.")
            if check_out <= check_in:
                raise forms.ValidationError(
                    "Check-out date must be after check-in date.")

        room = self.instance.room
        if room and number_of_guests:
            if number_of_guests > room.capacity:
                raise forms.ValidationError(
                    f"This room can only accommodate {room.capacity} guests."
                )
            if number_of_guests > room.available_beds:
                raise forms.ValidationError(
                    f"Only {room.available_beds} beds are available in this room."
                )

        if room and check_in and check_out:
            overlapping_bookings = Booking.objects.filter(
                room=room,
                status__in=['pending', 'confirmed'],
                check_in__lt=check_out,
                check_out__gt=check_in
            ).exclude(pk=self.instance.pk)

            if overlapping_bookings.exists():
                raise forms.ValidationError(
                    "These new dates are unavailable. Please choose different dates."
                )

        return cleaned_data
    send_copy = forms.BooleanField(
        required=False,
        initial=True,
        label="Send a copy to my email",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class SiteSettingsForm(forms.ModelForm):
    """Form for managing site settings"""
    class Meta:
        from .models import SiteSettings
        model = SiteSettings
        exclude = ['created_at', 'updated_at']
        widgets = {
            'custom_css': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'style': 'font-family: monospace;'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'site_name': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'tagline': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True
            }),
        }


class EmailConfigForm(forms.ModelForm):
    """Form for email configuration"""
    class Meta:
        model = EmailConfig
        fields = '__all__'
        widgets = {
            'email_host': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'smtp.gmail.com'
            }),
            'email_port': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 65535
            }),
            'email_host_user': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your-email@gmail.com'
            }),
            'email_host_password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your email password or app password'
            }),
            'default_from_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'noreply@734hotel.com'
            }),
            'booking_confirmation_template': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Dear Guest,\n\nYour booking at 734 Hotel has been confirmed...'
            }),
            'booking_cancellation_template': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5
            }),
            'contact_reply_template': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        email_use_tls = cleaned_data.get('email_use_tls')
        email_use_ssl = cleaned_data.get('email_use_ssl')

        if email_use_tls and email_use_ssl:
            raise forms.ValidationError(
                "Cannot use both TLS and SSL. Please choose one."
            )

        return cleaned_data


class SMSConfigForm(forms.ModelForm):
    """Form for SMS configuration"""
    class Meta:
        model = SMSConfig
        fields = '__all__'
        widgets = {
            'api_key': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your API key'
            }),
            'api_secret': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your API secret'
            }),
            'account_sid': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Twilio Account SID'
            }),
            'auth_token': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Twilio Auth Token'
            }),
            'from_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1234567890'
            }),
            'booking_sms_template': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Hi there, your booking at 734 Hotel is confirmed. We will contact you shortly.'
            }),
            'reminder_sms_template': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        provider = cleaned_data.get('provider')

        # Validate based on provider
        if provider == 'twilio':
            if not cleaned_data.get('account_sid'):
                raise forms.ValidationError(
                    "Account SID is required for Twilio")
            if not cleaned_data.get('auth_token'):
                raise forms.ValidationError(
                    "Auth Token is required for Twilio")
            if not cleaned_data.get('from_number'):
                raise forms.ValidationError(
                    "From Number is required for Twilio")
        elif provider == 'custom':
            if not cleaned_data.get('api_url'):
                raise forms.ValidationError(
                    "API URL is required for custom provider")
        elif provider == 'arkesel':
            if not cleaned_data.get('api_key'):
                raise forms.ValidationError(
                    "API Key is required for Arkesel")
            if not cleaned_data.get('from_number'):
                raise forms.ValidationError(
                    "Sender ID is required for Arkesel")

        return cleaned_data


class TestEmailForm(forms.Form):
    """Form for testing email configuration"""
    test_email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'test@example.com',
            'required': True
        }),
        help_text="Send a test email to this address"
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional test message...'
        }),
        required=False
    )


class TestSMSForm(forms.Form):
    """Form for testing SMS configuration"""
    test_phone = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1234567890',
            'required': True
        }),
        help_text="Send a test SMS to this phone number"
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional test message...'
        }),
        required=False
    )


class DatabaseConfigForm(forms.ModelForm):
    """Form for database configuration"""

    class Meta:
        model = DatabaseConfig
        fields = '__all__'
        widgets = {
            'engine': forms.Select(attrs={'class': 'form-control'}),
            'sqlite_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'db.sqlite3'
            }),
            'postgres_name': forms.TextInput(attrs={'class': 'form-control'}),
            'postgres_user': forms.TextInput(attrs={'class': 'form-control'}),
            'postgres_password': forms.PasswordInput(attrs={'class': 'form-control'}),
            'postgres_host': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'localhost'
            }),
            'postgres_port': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '5432'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('engine') == 'postgresql':
            required_fields = ['postgres_name', 'postgres_user',
                               'postgres_password', 'postgres_host', 'postgres_port']
            missing = [
                field for field in required_fields if not cleaned_data.get(field)]
            if missing:
                raise forms.ValidationError(
                    "Please fill all PostgreSQL connection fields.")
        return cleaned_data


class AdminPasswordResetForm(forms.Form):
    """Form for admin to reset user passwords"""
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
            'required': True
        }),
        min_length=8,
        help_text="Password must be at least 8 characters long"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'required': True
        })
    )
    notify_user = forms.BooleanField(
        required=False,
        initial=True,
        label="Notify user via email",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data


class FeatureToggleForm(forms.Form):
    """Form for toggling website features"""
    enable_vibe_check = forms.BooleanField(
        required=False,
        label="Enable Vibe Check Section",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    enable_guestbook = forms.BooleanField(
        required=False,
        label="Enable Guestbook Section",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    enable_booking = forms.BooleanField(
        required=False,
        label="Enable Booking System",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    enable_map = forms.BooleanField(
        required=False,
        label="Enable Neighborhood Map",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    enable_animations = forms.BooleanField(
        required=False,
        label="Enable Animations",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    enable_email_notifications = forms.BooleanField(
        required=False,
        label="Enable Email Notifications",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
