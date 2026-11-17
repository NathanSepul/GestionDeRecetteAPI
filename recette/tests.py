from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from recette.import_web import _durees, _minutes
from recette.models import Recette, formater_duree
from typeRecette.models import TypeRecette
from user.models import User


class DureesImportTests(SimpleTestCase):
    def test_minutes_iso(self):
        self.assertEqual(_minutes('PT15M'), 15)
        self.assertEqual(_minutes('PT1H30M'), 90)
        self.assertEqual(_minutes('P0DT2H0M'), 120)
        self.assertEqual(_minutes('P1D'), 1440)
        self.assertIsNone(_minutes('PT0M'))
        self.assertIsNone(_minutes('20 minutes'))
        self.assertIsNone(_minutes(None))

    def test_repos_deduit_du_total(self):
        self.assertEqual(_durees({'prepTime': 'PT20M', 'cookTime': 'PT40M', 'totalTime': 'PT3H'}), (20, 40, 120))
        self.assertEqual(_durees({'prepTime': 'PT20M', 'cookTime': 'PT40M', 'totalTime': 'PT1H'}), (20, 40, None))
        # total seul : on ne sait pas le répartir
        self.assertEqual(_durees({'totalTime': 'PT1H'}), (None, None, None))

    def test_formater_duree(self):
        self.assertEqual(formater_duree(45), '45 min')
        self.assertEqual(formater_duree(120), '2 h')
        self.assertEqual(formater_duree(90), '1 h 30 min')


class RecetteInfosApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='chef@example.com', password='motdepasse123', is_active=True)
        self.type = TypeRecette.objects.create(user=self.user, type='Plat')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def creer(self, titre, **champs):
        return Recette.objects.create(user=self.user, typeRecette=self.type, titre=titre, portion=4, **champs)

    def titres(self, **params):
        res = self.client.get('/api/recette/', {'userId': self.user.id, **params})
        self.assertEqual(res.status_code, 200, res.data)
        return [r['titre'] for r in res.data['results']]

    def test_temps_total_dans_la_reponse(self):
        recette = self.creer('Quiche', tempsPreparation=20, tempsCuisson=40)
        res = self.client.get(f'/api/recette/{recette.id}/')
        self.assertEqual(res.data['tempsTotal'], 60)
        self.assertIsNone(self.client.get(f'/api/recette/{self.creer("Salade").id}/').data['tempsTotal'])

    def test_creation_formulaire_champs_vides(self):
        # Le front envoie du multipart : "" doit donner null
        res = self.client.post('/api/recette/', {
            'titre': 'Soupe', 'portion': 2, 'typeRecette': self.type.id, 'conseil': '',
            'tempsPreparation': '10', 'tempsCuisson': '', 'tempsRepos': '', 'cout': '1', 'difficulte': '',
        }, format='multipart')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual((res.data['tempsPreparation'], res.data['tempsCuisson'], res.data['cout'], res.data['difficulte']), (10, None, 1, None))

    def test_valeurs_invalides(self):
        res = self.client.post('/api/recette/', {'titre': 'X', 'portion': 2, 'typeRecette': self.type.id, 'cout': 4, 'tempsCuisson': -5}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('cout', res.data)
        self.assertIn('tempsCuisson', res.data)

    def test_filtres(self):
        self.creer('Rapide', tempsPreparation=10, cout=1, difficulte=1)
        self.creer('Longue', tempsPreparation=30, tempsRepos=120, cout=3, difficulte=2)
        self.creer('Inconnue')
        self.assertEqual(self.titres(tempsMax=30), ['Rapide'])
        self.assertEqual(self.titres(cout='1,2'), ['Rapide'])
        self.assertEqual(sorted(self.titres(difficulte='1,2')), ['Longue', 'Rapide'])
        self.assertEqual(self.client.get('/api/recette/', {'cout': 'abc'}).status_code, 400)

    def test_tri_valeurs_vides_en_dernier(self):
        self.creer('Rapide', tempsPreparation=10, cout=1)
        self.creer('Longue', tempsPreparation=30, tempsRepos=120, cout=3)
        self.creer('Inconnue')
        self.assertEqual(self.titres(orderBy='tempsTotal'), ['Rapide', 'Longue', 'Inconnue'])
        self.assertEqual(self.titres(orderBy='-tempsTotal'), ['Longue', 'Rapide', 'Inconnue'])
        self.assertEqual(self.titres(orderBy='-cout'), ['Longue', 'Rapide', 'Inconnue'])
