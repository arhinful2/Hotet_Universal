from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
import string
import secrets
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.generic import TemplateView
from django.contrib.auth.models import User
import json
import requests
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from urllib.parse import urlencode
from django.urls import reverse

from .models import (
    SiteSettings, HeroSection, VibeCheckItem, Room, RoomImage,
    NeighborhoodPoint, GuestbookEntry, Booking,
    ContactMessage, Notification, SocialMedia,
    AnimationSetting, CustomStyle, EmailConfig, SMSConfig, ServiceItem,
    PaymentSettings, PaymentProviderConfig, BookingPayment
)
from .forms import BookingForm, ContactForm, GuestbookForm, AdminReplyForm, GuestBookingManageForm
from .signals import create_notification


def _build_callback_url(request, provider):
    if provider.callback_url:
        return provider.callback_url
    return request.build_absolute_uri(reverse('payment_success'))


def _create_provider_checkout(request, payment):
    provider = payment.provider
    booking = payment.booking
    amount_minor = int((payment.amount or Decimal('0')) * 100)
    callback_url = _build_callback_url(request, provider)

    if provider.provider == 'stripe':
        endpoint = provider.api_base_url or 'https://api.stripe.com/v1/checkout/sessions'
        success_url = request.build_absolute_uri(
            reverse('payment_success')) + f"?tx={payment.reference}&session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = request.build_absolute_uri(
            reverse('payment_cancel')) + f"?tx={payment.reference}"

        payload = {
            'mode': 'payment',
            'success_url': success_url,
            'cancel_url': cancel_url,
            'client_reference_id': payment.reference,
            'customer_email': booking.guest_email,
            'line_items[0][price_data][currency]': payment.currency.lower(),
            'line_items[0][price_data][product_data][name]': f"Booking #{booking.id} - {booking.room.name}",
            'line_items[0][price_data][unit_amount]': str(amount_minor),
            'line_items[0][quantity]': '1',
            'metadata[booking_id]': str(booking.id),
            'metadata[payment_reference]': payment.reference,
        }
        response = requests.post(
            endpoint,
            data=payload,
            headers={'Authorization': f'Bearer {provider.secret_key}'},
            timeout=25
        )
        body = response.json()
        if response.status_code >= 400 or not body.get('url'):
            raise ValueError(body.get('error', {}).get(
                'message', 'Stripe checkout session failed.'))
        return {
            'checkout_url': body.get('url'),
            'external_reference': body.get('id', ''),
            'provider_response': body,
            'status': 'pending'
        }

    if provider.provider == 'paystack':
        endpoint = provider.api_base_url or 'https://api.paystack.co/transaction/initialize'
        payload = {
            'email': booking.guest_email,
            'amount': amount_minor,
            'currency': payment.currency,
            'reference': payment.reference,
            'callback_url': request.build_absolute_uri(reverse('payment_success')) + f"?tx={payment.reference}",
            'metadata': {
                'booking_id': booking.id,
                'guest_name': booking.guest_name,
            }
        }
        response = requests.post(
            endpoint,
            json=payload,
            headers={
                'Authorization': f'Bearer {provider.secret_key}',
                'Content-Type': 'application/json'
            },
            timeout=25
        )
        body = response.json()
        data = body.get('data') or {}
        if response.status_code >= 400 or not data.get('authorization_url'):
            raise ValueError(
                body.get('message', 'Paystack initialization failed.'))
        return {
            'checkout_url': data.get('authorization_url'),
            'external_reference': data.get('reference', payment.reference),
            'provider_response': body,
            'status': 'pending'
        }

    if provider.provider == 'paypal':
        base = provider.api_base_url or 'https://api-m.sandbox.paypal.com'
        token_response = requests.post(
            f"{base}/v1/oauth2/token",
            data={'grant_type': 'client_credentials'},
            auth=(provider.public_key, provider.secret_key),
            timeout=25
        )
        token_body = token_response.json()
        access_token = token_body.get('access_token')
        if token_response.status_code >= 400 or not access_token:
            raise ValueError(token_body.get(
                'error_description', 'Unable to authenticate with PayPal.'))

        order_payload = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'reference_id': payment.reference,
                'description': f"Booking #{booking.id} - {booking.room.name}",
                'amount': {
                    'currency_code': payment.currency,
                    'value': str(payment.amount)
                }
            }],
            'application_context': {
                'return_url': request.build_absolute_uri(reverse('payment_success')) + f"?tx={payment.reference}",
                'cancel_url': request.build_absolute_uri(reverse('payment_cancel')) + f"?tx={payment.reference}",
            }
        }
        order_response = requests.post(
            f"{base}/v2/checkout/orders",
            json=order_payload,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            timeout=25
        )
        order_body = order_response.json()
        links = order_body.get('links') or []
        approve_link = next(
            (item.get('href')
             for item in links if item.get('rel') == 'approve'),
            ''
        )
        if order_response.status_code >= 400 or not approve_link:
            raise ValueError('PayPal checkout creation failed.')
        return {
            'checkout_url': approve_link,
            'external_reference': order_body.get('id', ''),
            'provider_response': order_body,
            'status': 'pending'
        }

    if provider.provider in ['momo', 'custom'] and provider.checkout_url_template:
        checkout_url = provider.checkout_url_template.format(
            amount=str(payment.amount),
            amount_minor=amount_minor,
            email=booking.guest_email,
            reference=payment.reference,
            currency=payment.currency,
            callback_url=callback_url,
        )
        return {
            'checkout_url': checkout_url,
            'external_reference': payment.reference,
            'provider_response': {'mode': 'template-url'},
            'status': 'pending'
        }

    raise ValueError(
        'Payment provider is not fully configured in admin. Please check credentials and templates.')


def _verify_payment(payment, request):
    provider = payment.provider

    if provider.provider == 'stripe' and payment.external_reference:
        endpoint = (provider.api_base_url or
                    'https://api.stripe.com/v1/checkout/sessions')
        response = requests.get(
            f"{endpoint}/{payment.external_reference}",
            headers={'Authorization': f'Bearer {provider.secret_key}'},
            timeout=25
        )
        data = response.json()
        if response.status_code < 400 and data.get('payment_status') == 'paid':
            return True, data
        return False, data

    if provider.provider == 'paystack':
        endpoint = (provider.api_base_url or
                    'https://api.paystack.co/transaction/verify')
        response = requests.get(
            f"{endpoint}/{payment.reference}",
            headers={'Authorization': f'Bearer {provider.secret_key}'},
            timeout=25
        )
        body = response.json()
        data = body.get('data') or {}
        if response.status_code < 400 and data.get('status') == 'success':
            return True, body
        return False, body

    return False, {'message': 'Manual verification required for this provider.'}


def index(request):
    """Main website view"""
    site_settings = SiteSettings.objects.first()

    # Get all active components
    context = {
        'hero_sections': HeroSection.objects.filter(is_active=True).order_by('order'),
        'rooms': Room.objects.filter(is_available=True).order_by('order'),
        'room_images': {},  # We'll populate this separately for each room
        'vibe_items': VibeCheckItem.objects.filter(is_active=True).order_by('order'),
        'neighborhood_points': NeighborhoodPoint.objects.filter(is_active=True),
        'guestbook_entries': GuestbookEntry.objects.filter(is_approved=True).order_by('-created_at')[:50],
        'social_media': SocialMedia.objects.filter(is_active=True).order_by('order'),
        'animations': AnimationSetting.objects.filter(enabled=True),
        'custom_styles': CustomStyle.objects.filter(is_active=True),
        'services': ServiceItem.objects.filter(is_active=True).order_by('order'),
        'booking_form': BookingForm(),
        'contact_form': ContactForm(),
        'guestbook_form': GuestbookForm(),
    }

    # Get room images for each room
    for room in context['rooms']:
        context['room_images'][room.id] = room.room_images.filter(
            is_active=True).order_by('order')

    return render(request, 'website/index.html', context)


def room_detail(request, room_id):
    """Room detail view with image slider"""
    room = get_object_or_404(Room, id=room_id, is_available=True)
    room_images = room.room_images.filter(is_active=True).order_by('order')

    context = {
        'room': room,
        'room_images': room_images,
        'booking_form': BookingForm(initial={'room': room}),
    }

    return render(request, 'website/room_detail.html', context)


def vibe_check_audio(request, item_id):
    """Serve vibe check audio"""
    vibe_item = get_object_or_404(VibeCheckItem, id=item_id)

    if vibe_item.audio_file:
        return JsonResponse({
            'audio_url': vibe_item.audio_file.url,
            'guest_note': vibe_item.guest_note,
            'guest_name': vibe_item.guest_name,
            'guest_country': vibe_item.guest_country
        })
    elif vibe_item.audio_url:
        return JsonResponse({
            'audio_url': vibe_item.audio_url,
            'guest_note': vibe_item.guest_note,
            'guest_name': vibe_item.guest_name,
            'guest_country': vibe_item.guest_country
        })

    return JsonResponse({'error': 'No audio available'}, status=404)


@require_POST
def submit_booking(request):
    """Handle booking form submission"""
    form = BookingForm(request.POST)
    site_settings = SiteSettings.objects.first()

    if form.is_valid():
        booking = form.save(commit=False)

        # Calculate total price
        nights = (booking.check_out - booking.check_in).days
        if nights > 0:
            booking.total_price = booking.room.price_per_night * nights
        booking.save()

        # Create notification
        if site_settings and site_settings.enable_email_notifications:
            create_notification(
                notification_type='booking',
                title=f'New Booking from {booking.guest_name}',
                message=f'New booking received for {booking.room.name}',
                related_object_id=booking.id,
                related_object_type='booking'
            )

            # Send email notification to admin
            try:
                email_config = EmailConfig.objects.filter(
                    is_active=True).first()
                if email_config and email_config.send_booking_emails:
                    subject = f'New Booking: {booking.guest_name} - {booking.room.name}'
                    message = render_to_string('email/new_booking.html', {
                        'booking': booking,
                        'site_name': site_settings.site_name
                    })

                    email = EmailMessage(
                        subject=subject,
                        body=message,
                        from_email=email_config.default_from_email,
                        to=[site_settings.notification_email],
                    )
                    email.content_subtype = "html"
                    email.send()

            except Exception as e:
                print(f"Email sending failed: {e}")

        manage_path = reverse('manage_booking', kwargs={
            'token': booking.guest_access_token})
        manage_url = request.build_absolute_uri(manage_path)

        messages.success(
            request, 'Booking submitted successfully! You can manage this booking from your private link.')
        return JsonResponse({
            'success': True,
            'message': 'Booking submitted successfully!',
            'booking_id': booking.id,
            'manage_url': manage_url,
            'manage_token': str(booking.guest_access_token),
        })

    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@require_GET
def booking_availability(request):
    """Check room availability for a date range"""
    room_id = request.GET.get('room_id')
    check_in_raw = request.GET.get('check_in')
    check_out_raw = request.GET.get('check_out')

    if not room_id:
        return JsonResponse({'success': False, 'error': 'Room is required.'}, status=400)

    try:
        room = Room.objects.get(id=room_id, is_available=True)
    except Room.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Selected room is unavailable.'}, status=404)

    room_unavailable_bookings = Booking.objects.filter(
        room=room,
        status__in=['pending', 'confirmed']
    ).order_by('check_in')

    room_unavailable_ranges = [
        {
            'check_in': booking.check_in.isoformat(),
            'check_out': booking.check_out.isoformat(),
            'status': booking.status
        }
        for booking in room_unavailable_bookings
    ]

    if not check_in_raw or not check_out_raw:
        return JsonResponse({
            'success': True,
            'available': True,
            'room_id': room.id,
            'unavailable_ranges': room_unavailable_ranges
        })

    try:
        check_in = datetime.strptime(check_in_raw, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_raw, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid date format.'}, status=400)

    if check_out <= check_in:
        return JsonResponse({'success': False, 'error': 'Check-out date must be after check-in date.'}, status=400)

    overlapping_bookings = Booking.objects.filter(
        room=room,
        status__in=['pending', 'confirmed'],
        check_in__lt=check_out,
        check_out__gt=check_in
    ).order_by('check_in')

    unavailable_ranges = [
        {
            'check_in': booking.check_in.isoformat(),
            'check_out': booking.check_out.isoformat(),
            'status': booking.status
        }
        for booking in overlapping_bookings
    ]

    return JsonResponse({
        'success': True,
        'available': not overlapping_bookings.exists(),
        'room_id': room.id,
        'unavailable_ranges': room_unavailable_ranges,
        'overlap_ranges': unavailable_ranges,
    })


def manage_booking(request, token):
    booking = get_object_or_404(Booking, guest_access_token=token)
    payment_settings = PaymentSettings.objects.first()
    active_providers = PaymentProviderConfig.objects.filter(
        is_active=True).order_by('priority', 'display_name')
    latest_payment = booking.payments.first()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'modify':
            if booking.status == 'cancelled':
                messages.error(
                    request, 'Cancelled bookings cannot be modified.')
                return redirect('manage_booking', token=token)

            has_paid_payment = booking.payments.filter(status='paid').exists()
            if has_paid_payment and payment_settings and not payment_settings.allow_guest_changes_after_payment:
                messages.error(
                    request, 'This booking has already been paid and can no longer be modified online.')
                return redirect('manage_booking', token=token)

            manage_form = GuestBookingManageForm(
                request.POST, instance=booking)
            if manage_form.is_valid():
                manage_form.save()
                messages.success(request, 'Booking updated successfully.')
                return redirect('manage_booking', token=token)
            messages.error(request, 'Please correct the errors below.')
        elif action == 'cancel':
            if booking.status == 'cancelled':
                messages.info(request, 'This booking is already cancelled.')
                return redirect('manage_booking', token=token)

            booking.status = 'cancelled'
            booking.cancelled_at = timezone.now()
            booking.cancellation_reason = (request.POST.get(
                'cancellation_reason') or '').strip()
            booking.save(update_fields=[
                         'status', 'cancelled_at', 'cancellation_reason', 'updated_at'])
            messages.success(request, 'Booking cancelled successfully.')
            return redirect('manage_booking', token=token)
        else:
            manage_form = GuestBookingManageForm(instance=booking)
    else:
        manage_form = GuestBookingManageForm(instance=booking)

    context = {
        'booking': booking,
        'manage_form': manage_form,
        'payment_settings': payment_settings,
        'active_providers': active_providers,
        'latest_payment': latest_payment,
    }
    return render(request, 'website/manage_booking.html', context)


@require_POST
def initiate_booking_payment(request, token, provider_id):
    booking = get_object_or_404(Booking, guest_access_token=token)
    settings_obj = PaymentSettings.objects.first()
    provider = get_object_or_404(
        PaymentProviderConfig, id=provider_id, is_active=True)

    if not settings_obj or not settings_obj.enable_online_payment:
        messages.error(
            request, 'Online payment is currently disabled by admin.')
        return redirect('manage_booking', token=token)

    if booking.status == 'cancelled':
        messages.error(
            request, 'Cannot process payment for a cancelled booking.')
        return redirect('manage_booking', token=token)

    amount = booking.total_price or booking.room.price_per_night
    if not amount or amount <= 0:
        messages.error(request, 'Invalid booking amount. Contact support.')
        return redirect('manage_booking', token=token)

    reference = f"BKG{booking.id}-{uuid.uuid4().hex[:12].upper()}"
    payment = BookingPayment.objects.create(
        booking=booking,
        provider=provider,
        amount=amount,
        currency=(settings_obj.default_currency or 'GHS').upper(),
        reference=reference,
        status='initiated',
    )

    try:
        payload = _create_provider_checkout(request, payment)
        payment.checkout_url = payload.get('checkout_url', '')
        payment.external_reference = payload.get('external_reference', '')
        payment.provider_response = payload.get('provider_response', {})
        payment.status = payload.get('status', 'pending')
        payment.save(update_fields=[
                     'checkout_url', 'external_reference', 'provider_response', 'status', 'updated_at'])
    except Exception as exc:
        payment.status = 'failed'
        payment.notes = str(exc)
        payment.save(update_fields=['status', 'notes', 'updated_at'])
        messages.error(request, f'Payment initialization failed: {exc}')
        return redirect('manage_booking', token=token)

    if payment.checkout_url:
        return redirect(payment.checkout_url)

    messages.info(
        request, 'Payment request created. Awaiting manual completion.')
    return redirect('manage_booking', token=token)


def payment_success(request):
    tx = request.GET.get('tx')
    if not tx:
        return render(request, 'website/payment_result.html', {
            'result_title': 'Payment status unavailable',
            'result_ok': False,
            'result_message': 'Missing transaction reference. Please contact support.'
        })

    payment = get_object_or_404(BookingPayment, reference=tx)
    is_paid, verify_response = _verify_payment(payment, request)

    if is_paid:
        payment.status = 'paid'
        payment.paid_at = timezone.now()
        payment.provider_response = verify_response
        payment.save(update_fields=['status', 'paid_at',
                     'provider_response', 'updated_at'])

        settings_obj = PaymentSettings.objects.first()
        if settings_obj and settings_obj.auto_confirm_booking_on_payment and payment.booking.status == 'pending':
            payment.booking.status = 'confirmed'
            payment.booking.save(update_fields=['status', 'updated_at'])

        return render(request, 'website/payment_result.html', {
            'result_title': 'Payment successful',
            'result_ok': True,
            'result_message': 'Your payment has been confirmed.',
            'booking': payment.booking,
        })

    if payment.status not in ['paid', 'cancelled']:
        payment.status = 'pending'
        payment.provider_response = verify_response
        payment.save(update_fields=[
                     'status', 'provider_response', 'updated_at'])

    return render(request, 'website/payment_result.html', {
        'result_title': 'Payment submitted',
        'result_ok': False,
        'result_message': 'We could not auto-verify this payment yet. Please wait for admin confirmation.',
        'booking': payment.booking,
    })


def payment_cancel(request):
    tx = request.GET.get('tx')
    payment = BookingPayment.objects.filter(
        reference=tx).first() if tx else None
    if payment and payment.status not in ['paid', 'cancelled']:
        payment.status = 'cancelled'
        payment.save(update_fields=['status', 'updated_at'])

    return render(request, 'website/payment_result.html', {
        'result_title': 'Payment cancelled',
        'result_ok': False,
        'result_message': 'No payment was completed. You can try again from your booking management page.',
        'booking': payment.booking if payment else None,
    })


@require_POST
def submit_contact(request):
    """Handle contact form submission"""
    form = ContactForm(request.POST)
    site_settings = SiteSettings.objects.first()

    if form.is_valid():
        contact = form.save(commit=False)
        contact.ip_address = request.META.get('REMOTE_ADDR')
        contact.save()

        # Create notification
        if site_settings and site_settings.enable_email_notifications:
            create_notification(
                notification_type='contact',
                title=f'New Message from {contact.name}',
                message=contact.subject,
                related_object_id=contact.id,
                related_object_type='contact'
            )

            # Send email notification to admin
            try:
                email_config = EmailConfig.objects.filter(
                    is_active=True).first()
                if email_config and email_config.send_contact_emails:
                    subject = f'New Contact Message: {contact.subject}'
                    message = render_to_string('email/new_contact.html', {
                        'contact': contact,
                        'site_name': site_settings.site_name
                    })

                    email = EmailMessage(
                        subject=subject,
                        body=message,
                        from_email=email_config.default_from_email,
                        to=[site_settings.notification_email],
                    )
                    email.content_subtype = "html"
                    email.send()

            except Exception as e:
                print(f"Email sending failed: {e}")

        messages.success(
            request, 'Message sent successfully! We will reply soon.')
        return JsonResponse({'success': True, 'message': 'Message sent successfully!'})

    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@require_POST
def submit_guestbook(request):
    """Handle guestbook form submission"""
    form = GuestbookForm(request.POST)

    if form.is_valid():
        entry = form.save(commit=False)
        entry.ip_address = request.META.get('REMOTE_ADDR')
        entry.save()

        # Create notification
        site_settings = SiteSettings.objects.first()
        if site_settings and site_settings.enable_email_notifications:
            create_notification(
                notification_type='guestbook',
                title=f'New Guestbook Entry from {entry.name}',
                message=entry.message[:100] + '...',
                related_object_id=entry.id,
                related_object_type='guestbook'
            )

        messages.success(
            request, 'Thank you for your message! It will appear after approval.')
        return JsonResponse({'success': True, 'message': 'Entry submitted successfully!'})

    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@require_GET
def get_guestbook_entries(request):
    """Get guestbook entries for AJAX loading"""
    entries = GuestbookEntry.objects.filter(
        is_approved=True).order_by('-created_at')[:50]
    data = []

    for entry in entries:
        data.append({
            'id': entry.id,
            'name': entry.name,
            'hometown': entry.hometown,
            'message': entry.message,
            'color': entry.color,
            'created_at': entry.created_at.strftime('%b %d, %Y')
        })

    return JsonResponse({'entries': data})


@require_GET
def get_neighborhood_points(request):
    """Get neighborhood points for the map"""
    points = NeighborhoodPoint.objects.filter(is_active=True)
    data = []

    for point in points:
        data.append({
            'id': point.id,
            'title': point.title,
            'description': point.description,
            'type': point.point_type,
            'lat': float(point.latitude),
            'lng': float(point.longitude),
            'icon': point.icon,
            'color': point.color
        })

    return JsonResponse({'points': data})


@require_GET
def get_room_images(request, room_id):
    """Get room images for AJAX loading"""
    room = get_object_or_404(Room, id=room_id)
    images = room.room_images.filter(is_active=True).order_by('order')
    data = []

    for image in images:
        data.append({
            'id': image.id,
            'url': image.image.url,
            'caption': image.caption,
            'order': image.order
        })

    return JsonResponse({'images': data})


def admin_dashboard(request):
    """Admin dashboard view"""
    if not request.user.is_staff:
        return redirect('admin:login')

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

    # Weekly bookings for the last 4 weeks
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

    # Get email and SMS configurations
    email_config = EmailConfig.objects.filter(is_active=True).first()
    sms_config = SMSConfig.objects.filter(is_active=True).first()

    context = {
        'total_bookings': Booking.objects.count(),
        'pending_bookings': Booking.objects.filter(status='pending').count(),
        'new_messages': ContactMessage.objects.filter(status='new').count(),
        'guestbook_entries': GuestbookEntry.objects.filter(is_approved=True).count(),
        'recent_bookings': Booking.objects.filter(created_at__gte=week_ago),
        'recent_messages': ContactMessage.objects.filter(created_at__gte=week_ago),
        'unread_notifications': Notification.objects.filter(is_read=False).count(),
        'site_settings': SiteSettings.objects.first(),
        'email_config': email_config,
        'sms_config': sms_config,
        'monthly_bookings': list(monthly_bookings),
        'weekly_bookings': list(weekly_bookings),
        'daily_bookings': list(daily_bookings),
    }

    return render(request, 'admin/custom_dashboard.html', context)


@csrf_exempt
@require_POST
def admin_send_reply(request):
    """Handle admin reply to messages"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    data = json.loads(request.body)
    message_id = data.get('message_id')
    reply_text = data.get('reply')

    contact = get_object_or_404(ContactMessage, id=message_id)

    try:
        # Get email config
        email_config = EmailConfig.objects.filter(is_active=True).first()
        from_email = email_config.default_from_email if email_config else settings.DEFAULT_FROM_EMAIL

        # Send email
        subject = f"Re: {contact.subject}"
        message = f"Dear {contact.name},\n\n{reply_text}\n\nBest regards,\n{request.user.get_full_name() or '734 Hotel Team'}"

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[contact.email],
            fail_silently=False,
        )

        # Update contact message
        contact.status = 'replied'
        contact.admin_response = reply_text
        contact.admin_responded_by = request.user
        contact.admin_responded_at = timezone.now()
        contact.save()

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def get_admin_notifications(request):
    """Get notifications for admin portal"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    notifications = Notification.objects.filter(
        is_read=False).order_by('-created_at')[:10]
    data = []

    for notification in notifications:
        data.append({
            'id': notification.id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'created_at': notification.created_at.strftime('%H:%M'),
            'url': f'/admin/website/{notification.related_object_type}/{notification.related_object_id}/change/'
        })

    return JsonResponse({'notifications': data})


@require_POST
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    notification = get_object_or_404(Notification, id=notification_id)
    notification.is_read = True
    notification.read_by = request.user
    notification.read_at = timezone.now()
    notification.save()

    return JsonResponse({'success': True})


def test_email_config(request):
    """Test email configuration"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    email_config = EmailConfig.objects.filter(is_active=True).first()
    if not email_config:
        return JsonResponse({'error': 'No active email configuration found'}, status=400)

    try:
        subject = 'Test Email from 734 Hotel'
        message = 'This is a test email to verify your email configuration.'

        send_mail(
            subject=subject,
            message=message,
            from_email=email_config.default_from_email,
            recipient_list=[
                email_config.test_email_address or request.user.email],
            fail_silently=False,
        )

        return JsonResponse({'success': True, 'message': 'Test email sent successfully!'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def dynamic_css(request):
    """Generate dynamic CSS based on admin settings"""
    site_settings = SiteSettings.objects.first()

    if not site_settings:
        return HttpResponse('', content_type='text/css')

    css = f"""
    :root {{
        --primary-color: {site_settings.primary_color or '#2C3E50'};
        --secondary-color: {site_settings.secondary_color or '#34495E'};
        --accent-color: {site_settings.accent_color or '#E74C3C'};
        --background-color: {site_settings.background_color or '#ECF0F1'};
        --text-color: {site_settings.text_color or '#2C3E50'};
        --font-family: {site_settings.font_family or "'Inter', sans-serif"};
        --heading-font: {site_settings.heading_font or "'Poppins', sans-serif"};
    }}
    
    body {{
        font-family: var(--font-family);
        color: var(--text-color);
        background-color: var(--background-color);
        line-height: 1.7;
    }}
    
    h1, h2, h3, h4, h5, h6 {{
        font-family: var(--heading-font);
        font-weight: 600;
        letter-spacing: -0.02em;
    }}
    
    .btn {{
        font-weight: 600;
        letter-spacing: 0.5px;
        border-radius: 8px;
        padding: 12px 24px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    
    .btn-primary {{
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        border: none;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }}
    
    .btn-primary:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
    }}
    
    .btn-secondary {{
        background-color: var(--secondary-color);
        border-color: var(--secondary-color);
    }}
    
    .accent-bg {{
        background-color: var(--accent-color);
    }}
    
    .text-accent {{
        color: var(--accent-color);
    }}
    
    /* Professional card styling */
    .room-card, .booking-widget, .contact-form {{
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
    }}
    
    /* Professional form styling */
    .form-control {{
        border: 2px solid #E1E8ED;
        border-radius: 8px;
        padding: 14px 16px;
        font-size: 16px;
        transition: all 0.3s ease;
    }}
    
    .form-control:focus {{
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(44, 62, 80, 0.1);
        outline: none;
    }}
    
    /* Professional section styling */
    .section {{
        padding: 80px 0;
    }}
    
    .section-title h2 {{
        font-size: 2.8rem;
        margin-bottom: 1.5rem;
        position: relative;
    }}
    
    .section-title h2::after {{
        content: '';
        position: absolute;
        bottom: -15px;
        left: 50%;
        transform: translateX(-50%);
        width: 80px;
        height: 4px;
        background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
        border-radius: 2px;
    }}
    
    /* Hero slider styling */
    .hero-slider {{
        height: 100vh;
        position: relative;
        overflow: hidden;
    }}
    
    .hero-slide {{
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        opacity: 0;
        transition: opacity 1s ease-in-out;
        z-index: 1;
    }}
    
    .hero-slide.active {{
        opacity: 1;
        z-index: 2;
    }}
    
    /* Room image slider */
    .room-slider {{
        position: relative;
        overflow: hidden;
        border-radius: 16px;
    }}
    
    .room-slide {{
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        opacity: 0;
        transition: opacity 0.5s ease-in-out;
    }}
    
    .room-slide.active {{
        opacity: 1;
        position: relative;
    }}
    
    /* Add custom CSS from admin */
    {site_settings.custom_css}
    """

    # Add custom styles
    custom_styles = CustomStyle.objects.filter(is_active=True)
    for style in custom_styles:
        css += f"\n{style.css_code}"

    return HttpResponse(css, content_type='text/css')


# ============================================
# ADMIN CREDENTIAL MANAGEMENT FUNCTIONS
# ============================================


def generate_random_password(length=12):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def admin_action_log(request, action_type, object_type='', object_id=None, object_repr=''):
    """Log admin actions for security"""
    try:
        from .models import AdminActionLog
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
        print(f"Failed to log admin action: {str(e)}")


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


def admin_credential_manager(request):
    """Admin credential management view"""
    if not request.user.is_staff:
        return redirect('/admin/login/')

    # Get all admin users
    admin_users = User.objects.filter(is_staff=True).order_by('-date_joined')

    # Get statistics
    stats = {
        'total_admins': User.objects.filter(is_staff=True).count(),
        'active_admins': User.objects.filter(is_staff=True, is_active=True).count(),
        'superusers': User.objects.filter(is_superuser=True).count(),
        'recent_logins': User.objects.filter(last_login__isnull=False).order_by('-last_login')[:5],
    }

    context = {
        'admin_users': admin_users,
        'admin_stats': stats,
        'total_users': User.objects.count(),
    }

    return render(request, 'admin/admin_credential_manager.html', context)


class AdminCredentialManagerView(TemplateView):
    template_name = 'admin/admin_credential_manager.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return redirect('/admin/login/')

        # Get all admin users
        admin_users = User.objects.filter(
            is_staff=True).order_by('-date_joined')

        # Get statistics
        stats = {
            'total_admins': User.objects.filter(is_staff=True).count(),
            'active_admins': User.objects.filter(is_staff=True, is_active=True).count(),
            'superusers': User.objects.filter(is_superuser=True).count(),
            'recent_logins': User.objects.filter(last_login__isnull=False).order_by('-last_login')[:5],
        }

        context = {
            'admin_users': admin_users,
            'admin_stats': stats,
            'total_users': User.objects.count(),
        }

        return self.render_to_response(context)


@require_POST
def create_admin_account(request):
    """Create new admin account"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        email = request.POST.get('email')
        username = request.POST.get('username')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        send_email = request.POST.get('send_email', 'true').lower() == 'true'

        if not email:
            messages.error(request, "Email is required")
            return redirect('admin_credential_manager')

        # Check if user exists
        if User.objects.filter(email=email).exists():
            messages.error(request, f"User with email {email} already exists")
            return redirect('admin_credential_manager')

        # Generate random password
        password = generate_random_password()

        # Create user
        user = User.objects.create_user(
            username=username or email.split('@')[0],
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
            send_mail(
                subject='Your 734 Hotel Admin Portal Credentials',
                message=f"""
                Hello {user.username},
                
                Your admin account has been created successfully!
                
                Login Credentials:
                - Username: {user.username}
                - Password: {password}
                - Admin URL: {request.build_absolute_uri('/admin/')}
                
                Please change your password after first login.
                
                Best regards,
                734 Hotel Team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(
                request, f"Admin user created and credentials sent to {email}")
        else:
            messages.success(
                request, f"Admin user created. Password: {password}")

        return redirect('admin_credential_manager')

    except Exception as e:
        messages.error(request, f"Error creating admin: {str(e)}")
        return redirect('admin_credential_manager')


@require_POST
def reset_admin_password(request, user_id):
    """Reset admin account password"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        user = get_object_or_404(User, id=user_id, is_staff=True)

        # Generate new password
        new_password = generate_random_password()

        # Set new password
        user.set_password(new_password)
        user.save()

        # Log the action
        admin_action_log(request, 'password_reset', 'User', user.id, str(user))

        # Send email
        send_email = request.POST.get('send_email', 'true').lower() == 'true'
        if send_email and user.email:
            send_mail(
                subject='734 Hotel Admin - Password Reset',
                message=f"""
                Hello {user.username},
                
                Your password has been reset.
                
                New Password: {new_password}
                
                Please change your password after logging in.
                
                Login URL: {request.build_absolute_uri('/admin/')}
                
                Best regards,
                734 Hotel Team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            messages.success(
                request, f"Password reset and email sent to {user.email}")
        else:
            messages.success(
                request, f"Password reset. New password: {new_password}")

        return redirect('admin_credential_manager')

    except Exception as e:
        messages.error(request, f"Error resetting password: {str(e)}")
        return redirect('admin_credential_manager')


@require_POST
def toggle_admin_status(request, user_id):
    """Activate/deactivate admin account"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        user = get_object_or_404(User, id=user_id, is_staff=True)

        # Don't let them deactivate themselves
        if user == request.user:
            messages.error(request, "You cannot deactivate your own account")
            return redirect('admin_credential_manager')

        # Toggle active status
        user.is_active = not user.is_active
        user.save()

        # Log the action
        action = 'activate' if user.is_active else 'deactivate'
        admin_action_log(request, 'update', 'User',
                         user.id, f"{action}d {str(user)}")

        status = "activated" if user.is_active else "deactivated"
        messages.success(request, f"Admin account {status} successfully")

        return redirect('admin_credential_manager')

    except Exception as e:
        messages.error(request, f"Error toggling admin status: {str(e)}")
        return redirect('admin_credential_manager')


def reset_admin_account_password(request, user_id):
    """Reset admin account password"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        user = get_object_or_404(User, id=user_id, is_staff=True)

        # Generate new password
        new_password = generate_random_password()
        user.set_password(new_password)
        user.save()

        # Log the action
        admin_action_log(request, 'password_reset', 'User',
                         user.id, f"Password reset for {str(user)}")

        # Send email notification
        try:
            send_mail(
                subject='Your 734 Hotel Admin Password Has Been Reset',
                message=f"""
                Hello {user.username},
                
                Your admin account password has been reset.
                
                New Password: {new_password}
                
                Please login and change your password immediately.
                
                Admin URL: {request.build_absolute_uri('/admin/')}
                
                Best regards,
                734 Hotel Team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            messages.success(
                request, f"Password reset and email sent to {user.email}")
        except Exception as email_error:
            messages.warning(
                request, f"Password reset successful, but email failed: {new_password}")

        return redirect('admin_credential_manager')

    except Exception as e:
        messages.error(request, f"Error resetting password: {str(e)}")
        return redirect('admin_credential_manager')


@require_POST
def delete_admin_account(request, user_id):
    """Delete admin account"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        user = get_object_or_404(User, id=user_id, is_staff=True)

        # Don't let them delete themselves
        if user == request.user:
            messages.error(request, "You cannot delete your own account")
            return redirect('admin_credential_manager')

        # Don't delete the last superuser
        if user.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
            messages.error(request, "Cannot delete the last superuser account")
            return redirect('admin_credential_manager')

        username = user.username
        user.delete()

        # Log the action
        admin_action_log(request, 'user_delete', 'User',
                         user_id, f"Deleted {username}")

        messages.success(
            request, f"Admin account {username} deleted successfully")

        return redirect('admin_credential_manager')

    except Exception as e:
        messages.error(request, f"Error deleting admin: {str(e)}")
        return redirect('admin_credential_manager')


def admin_password_reset_request(request):
    """Show password reset request form"""
    if request.method == 'POST':
        # Send password reset email
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email, is_staff=True)

            # Generate token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = request.build_absolute_uri(
                f'/admin/password-reset/{uid}/{token}/'
            )

            # Send email
            send_mail(
                subject='734 Hotel Admin - Password Reset Request',
                message=f"""
                Hello {user.username},
                
                You requested a password reset for your admin account.
                
                Click here to reset your password: {reset_url}
                
                This link will expire in 24 hours.
                
                If you didn't request this, please ignore this email.
                
                Best regards,
                734 Hotel Team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(request, f"Password reset email sent to {email}")
            return redirect('/admin/login/')

        except User.DoesNotExist:
            messages.error(request, "No admin account found with that email")

    return render(request, 'admin/password_reset_request.html')


def admin_password_reset_form(request, uidb64, token):
    """Show password reset form"""
    # Verify token
    is_valid, result = verify_admin_token(uidb64, token)
    if not is_valid:
        messages.error(request, result)
        return redirect('admin_password_reset_request')

    user = result

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, 'admin/password_reset_form.html', {
                'uidb64': uidb64,
                'token': token,
                'user': user,
            })

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters")
            return render(request, 'admin/password_reset_form.html', {
                'uidb64': uidb64,
                'token': token,
                'user': user,
            })

        # Set new password
        user.set_password(password)
        user.save()

        # Log the action (if possible)
        try:
            admin_action_log(request, 'password_reset',
                             'User', user.id, str(user))
        except:
            pass

        messages.success(
            request, "Password reset successfully. You can now login.")
        return redirect('/admin/login/')

    return render(request, 'admin/password_reset_form.html', {
        'uidb64': uidb64,
        'token': token,
        'user': user,
    })
