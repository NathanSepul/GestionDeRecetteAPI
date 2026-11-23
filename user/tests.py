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


class CreationDeCompteTests(TestCase):
    """Pas d'inscription libre : comptes créés dans l'admin, mot de passe choisi via « mot de passe oublié »."""

    def test_inscription_libre_desactivee(self):
        client = APIClient()
        res = client.post('/api/user/registration/register/', {'email': 'x@example.com', 'password': 'motdepasse123'}, format='json')
        self.assertEqual(res.status_code, 404)
        self.assertFalse(user.models.User.objects.filter(email='x@example.com').exists())
        self.assertEqual(client.post('/api/user/registration/verify-registration/', {}, format='json').status_code, 404)

    def test_creation_admin_sans_mot_de_passe_puis_lien_de_reinitialisation(self):
        from django.core import mail
        admin = user.models.User.objects.create_superuser(email='admin@example.com', password='motdepasse123')
        self.client.force_login(admin)
        res = self.client.post('/admin/user/user/add/', {
            'email': 'mamie@example.com', 'first_name': 'Mamie', 'last_name': 'Sepul', 'language': 'fr',
            'usable_password': 'false',
        })
        self.assertEqual(res.status_code, 302, res.content.decode()[:2000])
        mamie = user.models.User.objects.get(email='mamie@example.com')
        self.assertTrue(mamie.is_active)
        self.assertFalse(mamie.has_usable_password())

        res = APIClient().post('/api/user/registration/send-reset-password-link/', {'login': 'mamie@example.com'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reset-password-form', mail.outbox[0].body)


class ProfilApiTests(TestCase):
    """Le profil se lit et se modifie, mais ne se crée ni ne se supprime par l'API."""

    def setUp(self):
        self.chef = user.models.User.objects.create_user(email='chef@example.com', password='motdepasse123', is_active=True)
        self.client = APIClient()
        self.client.force_authenticate(self.chef)

    def test_pas_de_creation_par_l_api(self):
        res = self.client.post('/api/user/profile/', {'first_name': 'Pirate', 'last_name': 'X'}, format='json')
        self.assertEqual(res.status_code, 405)
        self.assertEqual(user.models.User.objects.count(), 1)

    def test_pas_de_suppression_par_l_api(self):
        self.assertEqual(self.client.delete(f'/api/user/profile/{self.chef.id}/').status_code, 405)
        self.assertTrue(user.models.User.objects.filter(pk=self.chef.pk).exists())

    def test_lecture_et_modification(self):
        self.assertEqual(self.client.get(f'/api/user/profile/{self.chef.id}/').status_code, 200)
        res = self.client.patch(f'/api/user/profile/{self.chef.id}/', {'first_name': 'Paul'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)


class ThrottlingTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # compteurs partagés avec les autres tests

    def tearDown(self):
        from django.core.cache import cache
        cache.clear()

    def test_login_limite(self):
        client = APIClient()
        codes = [client.post('/api/login/', {'email': 'x@example.com', 'password': 'faux'}, format='json').status_code
                 for _ in range(11)]
        self.assertEqual(codes[:10], [401] * 10)
        self.assertEqual(codes[10], 429)


class ValidateursMotDePasseTests(TestCase):
    def test_codes_d_erreur(self):
        from django.core.exceptions import ValidationError
        from gestionDeRecette.validators import LowercaseValidator, UppercaseValidator
        for validateur, mot_de_passe, code in ((UppercaseValidator(), 'minuscules', 'password_no_upper'),
                                               (LowercaseValidator(), 'MAJUSCULES', 'password_no_lower')):
            with self.assertRaises(ValidationError) as erreur:
                validateur.validate(mot_de_passe)
            self.assertEqual(erreur.exception.code, code)
