from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from recette.import_web import AnalyseurIngredients, _domaine_autorise, _durees, _ingredients, _minutes
from django.core.exceptions import ValidationError

from recette.models import Produit, Recette, SiteImport, Unite, formater_duree
from typeRecette.models import TypeRecette
from user.models import User


# Structure HTML de WP Recipe Maker, réduite à l'essentiel
PAGE_WPRM = """
<div class="wprm-recipe-ingredient-group">
  <ul class="wprm-recipe-ingredients"><li class="wprm-recipe-ingredient">200 g de nouilles</li></ul>
</div>
<div class="wprm-recipe-ingredient-group">
  <h4 class="wprm-recipe-group-name wprm-recipe-ingredient-group-name">Sauce</h4>
  <ul class="wprm-recipe-ingredients">
    <li class="wprm-recipe-ingredient">3 c. à s. de sucre</li>
    <li class="wprm-recipe-ingredient">1 c. à s. de <span>sauce soja</span></li>
  </ul>
</div>
"""


class GroupesWprmTests(SimpleTestCase):
    def test_sections_depuis_les_groupes(self):
        lignes = ['200 g de nouilles', '3 c. à s. de sucre', '1 c. à s. de sauce soja']
        self.assertEqual(_ingredients(lignes, PAGE_WPRM), [
            (False, '200 g de nouilles'), (True, 'Sauce'), (False, '3 c. à s. de sucre'), (False, '1 c. à s. de sauce soja'),
        ])

    def test_a_plat_si_le_compte_ne_correspond_pas(self):
        lignes = ['200 g de nouilles', '3 c. à s. de sucre']
        self.assertEqual(_ingredients(lignes, PAGE_WPRM), [(False, l) for l in lignes])

    def test_a_plat_sans_wprm(self):
        self.assertEqual(_ingredients(['1 oeuf'], '<ul><li>1 oeuf</li></ul>'), [(False, '1 oeuf')])


class NoteEntreParenthesesTests(TestCase):
    def setUp(self):
        for nom in ('ail', 'oignon', 'curcuma'):
            Produit.objects.get_or_create(nom=nom)
        Unite.objects.get_or_create(code='g', defaults={'description': 'gramme'})
        Unite.objects.get_or_create(code='cc', defaults={'description': 'cuillère à café'})
        self.analyseur = AnalyseurIngredients()

    def test_note_gardee_comme_preparation(self):
        _, _, produit, nom, preparation = self.analyseur.analyser("4 gousses d'ail (émincées)")
        self.assertEqual((produit.nom, nom, preparation), ('ail', None, 'émincées'))
        _, _, produit, _, preparation = self.analyseur.analyser('1 oignon ( tranché)')
        self.assertEqual((produit.nom, preparation), ('oignon', 'tranché'))

    def test_note_trop_longue_ligne_gardee(self):
        ligne = '2 c. à c. de curcuma (idéalement frais, sinon en poudre mais alors moitié moins)'
        _, _, produit, nom, preparation = self.analyseur.analyser(ligne)
        self.assertIsNone(produit)
        self.assertEqual((nom, preparation), ('curcuma (idéalement frais, sinon en poudre mais alors moitié moins)', ''))

    def test_produit_inconnu_note_dans_nom(self):
        _, _, produit, nom, preparation = self.analyseur.analyser('200 g de nouilles (poids sec)')
        self.assertEqual((produit, nom, preparation), (None, 'nouilles (poids sec)', ''))


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


class ImportSitesApiTests(TestCase):
    def test_liste_des_sites(self):
        client = APIClient()
        self.assertEqual(client.get('/api/recette/import-sites/').status_code, 401)
        client.force_authenticate(User.objects.create_user(email='chef@example.com', password='motdepasse123', is_active=True))
        res = client.get('/api/recette/import-sites/')
        self.assertEqual(res.status_code, 200)
        self.assertIn({'nom': 'Marmiton', 'domaine': 'marmiton.org', 'url': 'https://www.marmiton.org'}, res.json())


class PartageRecettesTests(TestCase):
    """App familiale fermée : toutes les recettes (importées comprises) sont partagées et copiables."""

    def setUp(self):
        self.alice = User.objects.create_user(email='alice@example.com', password='motdepasse123', is_active=True)
        self.bob = User.objects.create_user(email='bob@example.com', password='motdepasse123', is_active=True)
        type_alice = TypeRecette.objects.create(user=self.alice, type='Plat')
        self.type_bob = TypeRecette.objects.create(user=self.bob, type='Plat')
        self.importee = Recette.objects.create(
            user=self.alice, typeRecette=type_alice, titre='Dan Dan', portion=2,
            source='https://marcwiner.com/nouilles-dan-dan/', tempsPreparation=10, cout=1,
        )
        self.client = APIClient()

    def en_tant_que(self, user):
        self.client.force_authenticate(user)
        return self.client

    def test_recette_importee_visible_par_les_autres(self):
        client = self.en_tant_que(self.bob)
        titres = [r['titre'] for r in client.get('/api/recette/', {'userId': self.alice.id}).data['results']]
        self.assertEqual(titres, ['Dan Dan'])
        self.assertEqual(client.get(f'/api/recette/{self.importee.id}/').status_code, 200)

    def test_pdf_reserve_aux_utilisateurs_connectes(self):
        self.assertEqual(APIClient().get(f'/api/recette/{self.importee.id}/pdf/').status_code, 401)

    def test_copie_dans_son_livre(self):
        res = self.en_tant_que(self.bob).post('/api/recette/import/', {'recetteId': self.importee.id, 'typeRecette': self.type_bob.id}, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        copie = Recette.objects.get(pk=res.data['id'])
        self.assertEqual((copie.user, copie.titre, copie.source, copie.tempsPreparation, copie.cout),
                         (self.bob, 'Dan Dan', self.importee.source, 10, 1))

    def test_photo_importee_par_defaut(self):
        from recette.serializer import ImportUrlSerializer
        serializer = ImportUrlSerializer(data={'url': 'https://www.marmiton.org/x', 'typeRecette': 1})
        self.assertTrue(serializer.is_valid())
        self.assertTrue(serializer.validated_data['importerImage'])


class SitesImportTests(TestCase):
    """Liste blanche gérée dans l'admin (sites créés par la migration 0042)."""

    def test_sites_initiaux_autorises(self):
        self.assertTrue(_domaine_autorise('marcwiner.com'))
        self.assertTrue(_domaine_autorise('www.marmiton.org'))
        self.assertFalse(_domaine_autorise('colruyt.be'))
        self.assertFalse(_domaine_autorise('marmiton.org.example.com'))

    def test_site_ajoute_puis_desactive(self):
        site = SiteImport(nom='Colruyt', domaine='https://www.Colruyt.be/fr/recettes', url='https://www.colruyt.be/fr/recettes')
        site.full_clean()
        site.save()
        self.assertEqual(site.domaine, 'colruyt.be')
        self.assertTrue(_domaine_autorise('www.colruyt.be'))

        site.actif = False
        site.save()
        self.assertFalse(_domaine_autorise('www.colruyt.be'))
        client = APIClient()
        client.force_authenticate(User.objects.create_user(email='chef@example.com', password='motdepasse123', is_active=True))
        self.assertNotIn('Colruyt', [s['nom'] for s in client.get('/api/recette/import-sites/').json()])

    def test_domaine_invalide(self):
        with self.assertRaises(ValidationError):
            SiteImport(nom='X', domaine='localhost', url='https://example.com').full_clean()
