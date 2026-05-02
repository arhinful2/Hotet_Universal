from django.urls import path
from . import views

urlpatterns = [
    # Main website
    path('', views.index, name='index'),
    path('room/<int:room_id>/', views.room_detail, name='room_detail'),
    path('booking/manage/<uuid:token>/',
         views.manage_booking, name='manage_booking'),
    path('booking/manage/<uuid:token>/pay/<int:provider_id>/',
         views.initiate_booking_payment, name='initiate_booking_payment'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),

    # API endpoints
    path('api/vibe-check/<int:item_id>/',
         views.vibe_check_audio, name='vibe_check_audio'),
    path('api/bookings/submit/', views.submit_booking, name='submit_booking'),
    path('api/bookings/availability/', views.booking_availability,
         name='booking_availability'),
    path('api/contact/submit/', views.submit_contact, name='submit_contact'),
    path('api/guestbook/submit/', views.submit_guestbook, name='submit_guestbook'),
    path('api/guestbook/entries/', views.get_guestbook_entries,
         name='get_guestbook_entries'),
    path('api/neighborhood/points/', views.get_neighborhood_points,
         name='get_neighborhood_points'),
    path('api/room/<int:room_id>/images/',
         views.get_room_images, name='get_room_images'),

    # Admin API
    path('api/admin/notifications/', views.get_admin_notifications,
         name='get_admin_notifications'),
    path('api/admin/notifications/<int:notification_id>/read/',
         views.mark_notification_read, name='mark_notification_read'),
    path('api/admin/send-reply/', views.admin_send_reply, name='admin_send_reply'),
    path('api/admin/test-email/', views.test_email_config,
         name='test_email_config'),

    # Dynamic CSS
    path('dynamic.css', views.dynamic_css, name='dynamic_css'),


    # Admin credential management
    path('admin/credential-manager/',
         views.AdminCredentialManagerView.as_view(),
         name='admin_credential_manager'),

    path('admin/create-admin/',
         views.create_admin_account,
         name='create_admin_account'),

    path('admin/reset-password/<int:user_id>/',
         views.reset_admin_account_password,
         name='reset_admin_password'),

    path('admin/toggle-status/<int:user_id>/',
         views.toggle_admin_status,
         name='toggle_admin_status'),

    path('admin/delete-account/<int:user_id>/',
         views.delete_admin_account,
         name='delete_admin_account'),

    # Public password reset URLs
    path('admin/password-reset/',
         views.admin_password_reset_request,
         name='admin_password_reset_request'),

    path('admin/password-reset/<str:uidb64>/<str:token>/',
         views.admin_password_reset_form,
         name='admin_password_reset'),
]
