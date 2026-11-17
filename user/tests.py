from django.test import TestCase
from rest_framework.test import APIClient

from gestionDeRecette.api_views import REFRESH_COOKIE
import user.models


class RefreshCookieTests(TestCase):
    """Client web : refresh token en cookie HttpOnly ; app mobile : refresh token dans le JSON."""

    def setUp(self):
        self.client = APIClient()
        user.models.User.objects.create_user(email='chef@example.com', password='motdepasse123', is_active=True)

    def login(self, **extra):
        return self.client.post('/api/login/', {'email': 'chef@example.com', 'password': 'motdepasse123', **extra}, format='json')

    def test_login_mobile_inchange(self):
        res = self.login()
        self.assertEqual(res.status_code, 200)
        self.assertIn('refresh', res.data)
        self.assertNotIn(REFRESH_COOKIE, res.cookies)

    def test_login_web_pose_cookie_httponly(self):
        res = self.login(refresh_cookie=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)
        self.assertNotIn('refresh', res.data)
        cookie = res.cookies[REFRESH_COOKIE]
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Strict')
        self.assertEqual(cookie['path'], '/api/token/')

    def test_refresh_web_lit_le_cookie(self):
        self.login(refresh_cookie=True)  # APIClient garde le cookie
        res = self.client.post('/api/token/refresh/', {'refresh_cookie': True}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)
        self.assertNotIn('refresh', res.data)
        self.assertTrue(res.cookies[REFRESH_COOKIE].value)

    def test_refresh_web_sans_cookie(self):
        res = self.client.post('/api/token/refresh/', {'refresh_cookie': True}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_refresh_mobile_inchange(self):
        refresh = self.login().data['refresh']
        res = self.client.post('/api/token/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('refresh', res.data)

    def test_logout_blackliste_et_supprime_le_cookie(self):
        self.login(refresh_cookie=True)
        old = self.client.cookies[REFRESH_COOKIE].value
        res = self.client.post('/api/token/logout/')
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.cookies[REFRESH_COOKIE].value, '')
        # L'ancien refresh token ne marche plus
        self.client.cookies[REFRESH_COOKIE] = old
        res = self.client.post('/api/token/refresh/', {'refresh_cookie': True}, format='json')
        self.assertEqual(res.status_code, 401)
