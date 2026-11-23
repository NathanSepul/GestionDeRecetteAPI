import os
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from appVersion.admin import chemin_application
from appVersion.models import AppVersion
from user.models import User


class AdminUploadTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        admin = User.objects.create_superuser(email='admin@example.com', password='motdepasse123')
        self.client.force_login(admin)

    def envoyer(self, nom_fichier, contenu=b'zip'):
        with override_settings(MEDIA_ROOT=self.media.name):
            return self.client.post('/admin/appVersion/appversion/add/', {
                'version_number': '1.2.0', 'support': 'apk',
                'app_file': SimpleUploadedFile(nom_fichier, contenu),
            })

    def test_upload_puis_remplacement_archive_l_ancien(self):
        self.assertEqual(self.envoyer('MesRecettes.apk.zip', b'v1').status_code, 302)
        with override_settings(MEDIA_ROOT=self.media.name):
            chemin = chemin_application('apk')
        with open(chemin, 'rb') as f:
            self.assertEqual(f.read(), b'v1')

        AppVersion.objects.all().delete()  # support unique : on recrée la version
        self.assertEqual(self.envoyer('MesRecettes.apk.zip', b'v2').status_code, 302)
        with open(chemin, 'rb') as f:
            self.assertEqual(f.read(), b'v2')
        self.assertEqual(len(os.listdir(os.path.dirname(chemin))), 2)  # nouvelle version + archive

    def test_mauvaise_extension_message_clair(self):
        res = self.envoyer('MesRecettes.ipa.zip')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "reçu : &#x27;MesRecettes.ipa.zip&#x27;")
        self.assertFalse(AppVersion.objects.exists())
