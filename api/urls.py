from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    AttendanceEventView, AttendanceHistoryView, IncidentCreateView, 
    UserProfileView, UserFCMUpdateView, CustomTokenObtainPairView, TrackingConfigView,
    LocationPointCreateView, JourneyTrackingHistoryView, SyncStatusView,
    RolListView, TipoIncidenciaListView, SedeListCreateView, SedeDetailView, UsuarioViewSet,
    IncidenciaListView, AsistenciaListView, ActividadHoyView, ActividadDetalleUsuarioView,
    JornadaEstadoMarcacionView, JornadaConfiguracionViewSet, HistorialJornadaListView,
    HistorialJornadaDetalleView, JornadaActividadViewSet, JourneyTrackingMapView, JourneyTrackingRecorridoJornadaView,
    HorarioViewSet, UsuarioHorarioViewSet, IntercambioHorarioViewSet, SedesResumenView, DashboardResumenView,
    DatabaseConnectionCheckView, HistorialSedesResumenView
)

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'jornada-configuracion', JornadaConfiguracionViewSet, basename='jornada-configuracion')
router.register(r'jornada-actividades', JornadaActividadViewSet, basename='jornada-actividad')
router.register(r'horarios', HorarioViewSet, basename='horarios')
router.register(r'usuario-horarios', UsuarioHorarioViewSet, basename='usuario-horarios')
router.register(r'intercambios', IntercambioHorarioViewSet, basename='intercambios')

urlpatterns = [
    # Auth
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', UserProfileView.as_view(), name='user_profile'),
    path('users/me/fcm/', UserFCMUpdateView.as_view(), name='user_fcm_update'),
    path('sync/', SyncStatusView.as_view(), name='sync_status'),
    path('db-check/', DatabaseConnectionCheckView.as_view(), name='db_check'),
    
    # Attendance
    path('attendance/event/', AttendanceEventView.as_view(), name='attendance_event'),
    path('attendance/history/', AttendanceHistoryView.as_view(), name='attendance_history'),
    path('jornada/estado-marcacion/', JornadaEstadoMarcacionView.as_view(), name='estado_marcacion'),
    path('historial-jornadas/', HistorialJornadaListView.as_view(), name='historial_jornadas'),
    path('historial-jornadas/<int:pk>/detalle/', HistorialJornadaDetalleView.as_view(), name='historial_jornada_detalle'),
    
    # Incidents
    path('incidents/create/', IncidentCreateView.as_view(), name='incident_create'),

    # Tracking
    path('configuracion-tracking/', TrackingConfigView.as_view(), name='tracking_config'),
    path('ubicacion-puntos/', LocationPointCreateView.as_view(), name='location_points'),
    path('attendance/<int:asistencia_id>/points/', JourneyTrackingHistoryView.as_view(), name='journey_points'),
    path('tracking/recorrido-jornada/<int:historial_jornada_id>/', JourneyTrackingRecorridoJornadaView.as_view(), name='recorrido_jornada'),

    # Web Dashboard Endpoints
    path('dashboard/resumen/', DashboardResumenView.as_view(), name='dashboard_resumen'),
    path('roles/', RolListView.as_view(), name='rol_list'),
    path('tipos-incidencia/', TipoIncidenciaListView.as_view(), name='tipo_incidencia_list'),
    path('sedes/resumen/', SedesResumenView.as_view(), name='sedes_resumen'),
    path('sedes/historial-resumen/', HistorialSedesResumenView.as_view(), name='sedes_historial_resumen'),
    path('sedes/', SedeListCreateView.as_view(), name='sede_list_create'),
    path('sedes/<int:pk>/', SedeDetailView.as_view(), name='sede_detail'),
    path('incidencias/', IncidenciaListView.as_view(), name='incidencia_list'),
    path('asistencias/', AsistenciaListView.as_view(), name='asistencia_list'),
    path('actividad/hoy/', ActividadHoyView.as_view(), name='actividad_hoy'),
    path('actividad/usuario/<int:pk>/', ActividadDetalleUsuarioView.as_view(), name='actividad_detalle_usuario'),
    path('jornada/<int:asistencia_id>/mapa/', JourneyTrackingMapView.as_view(), name='jornada_mapa_externo'),
    path('', include(router.urls)),
]
