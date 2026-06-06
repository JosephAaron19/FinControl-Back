from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Usuario

class UserFCMUpdateTests(APITestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            dni='12345678',
            nombre_completo='Test User',
            password='testpassword'
        )
        self.url = reverse('user_fcm_update')

    def test_update_fcm_token_unauthenticated(self):
        # Unauthenticated request should return 401
        response = self.client.patch(self.url, {'fcm': 'test_token'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_fcm_token_missing_token(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'El token FCM es requerido'})

    def test_update_fcm_token_empty_token(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'fcm': '   '})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'El token FCM es requerido'})

    def test_update_fcm_token_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'fcm': 'token_de_prueba_123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'message': 'Token FCM actualizado correctamente',
            'user_id': self.user.id
        })
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.fcm, 'token_de_prueba_123')

