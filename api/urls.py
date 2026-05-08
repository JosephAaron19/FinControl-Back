from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    AttendanceEventView, AttendanceHistoryView, IncidentCreateView, 
    UserProfileView, CustomTokenObtainPairView, TrackingConfigView,
    LocationPointCreateView, JourneyTrackingHistoryView, SyncStatusView,
    RolListView, TipoIncidenciaListView, SedeListCreateView, SedeDetailView, UsuarioViewSet,
    IncidenciaListView, AsistenciaListView, ActividadHoyView, ActividadDetalleUsuarioView
)

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuario')

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

    # Web Dashboard Endpoints
    path('roles/', RolListView.as_view(), name='rol_list'),
    path('tipos-incidencia/', TipoIncidenciaListView.as_view(), name='tipo_incidencia_list'),
    path('sedes/', SedeListCreateView.as_view(), name='sede_list_create'),
    path('sedes/<int:pk>/', SedeDetailView.as_view(), name='sede_detail'),
    path('incidencias/', IncidenciaListView.as_view(), name='incidencia_list'),
    path('asistencias/', AsistenciaListView.as_view(), name='asistencia_list'),
    path('actividad/hoy/', ActividadHoyView.as_view(), name='actividad_hoy'),
    path('actividad/usuario/<int:pk>/', ActividadDetalleUsuarioView.as_view(), name='actividad_detalle_usuario'),
    path('', include(router.urls)),
]
