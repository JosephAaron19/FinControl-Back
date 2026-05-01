from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import AttendanceEventView, AttendanceHistoryView, IncidentCreateView, UserProfileView

urlpatterns = [
    # Auth
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', UserProfileView.as_view(), name='user_profile'),
    
    # Attendance
    path('attendance/event/', AttendanceEventView.as_view(), name='attendance_event'),
    path('attendance/history/', AttendanceHistoryView.as_view(), name='attendance_history'),
    
    # Incidents
    path('incidents/create/', IncidentCreateView.as_view(), name='incident_create'),
]
