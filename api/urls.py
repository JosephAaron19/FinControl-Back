from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    AttendanceEventView, AttendanceHistoryView, IncidentCreateView, 
    UserProfileView, CustomTokenObtainPairView, TrackingConfigView,
    LocationPointCreateView, JourneyTrackingHistoryView, SyncStatusView
)

urlpatterns = [
    # Auth
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', UserProfileView.as_view(), name='user_profile'),
    path('sync/', SyncStatusView.as_view(), name='sync_status'),
    
    # Attendance
    path('attendance/event/', AttendanceEventView.as_view(), name='attendance_event'),
    path('attendance/history/', AttendanceHistoryView.as_view(), name='attendance_history'),
    
    # Incidents
    path('incidents/create/', IncidentCreateView.as_view(), name='incident_create'),

    # Tracking
    path('configuracion-tracking/', TrackingConfigView.as_view(), name='tracking_config'),
    path('ubicacion-puntos/', LocationPointCreateView.as_view(), name='location_points'),
    path('attendance/<int:asistencia_id>/points/', JourneyTrackingHistoryView.as_view(), name='journey_points'),
]
