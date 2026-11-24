import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import anthropic
import httpx2 as httpx
from django.core import mail

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from recette.import_web import AnalyseurIngredients, _domaine_autorise, _durees, _ingredients, _minutes
from django.core.exceptions import ValidationError

from recette import import_ia, import_video
from recette.import_ia import ClaudeIndisponible
from recette.models import AppelIA, EtatClaude, Equivalence, Ingredient, ImportVideo, Synonyme, Produit, Recette, SiteImport, Unite, formater_duree
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

    def test_copie_garde_preparation_et_ordre(self):
        from recette.models import Ingredient, Preparation
        Ingredient.objects.create(recette=self.importee, noOrdre=0, isSection=True, nom='Sauce')
        Ingredient.objects.create(recette=self.importee, noOrdre=1, quantite=2, nom='oignons', preparation='émincés')
        Preparation.objects.create(recette=self.importee, noOrdre=0, description='Cuire')
        res = self.en_tant_que(self.bob).post('/api/recette/import/', {'recetteId': self.importee.id, 'typeRecette': self.type_bob.id}, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        copie = Recette.objects.get(pk=res.data['id'])
        self.assertEqual(
            list(copie.ingredient_set.order_by('noOrdre').values_list('noOrdre', 'isSection', 'nom', 'preparation')),
            [(0, True, 'Sauce', ''), (1, False, 'oignons', 'émincés')],
        )
        self.assertEqual(list(copie.preparation_set.values_list('description', flat=True)), ['Cuire'])

    def test_copie_titre_deja_pris(self):
        Recette.objects.create(user=self.bob, typeRecette=self.type_bob, titre='Dan Dan', portion=2)
        res = self.en_tant_que(self.bob).post('/api/recette/import/', {'recetteId': self.importee.id, 'typeRecette': self.type_bob.id}, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['titre'], 'Dan Dan (2)')

    def test_pdf_lit_l_image_sur_le_disque(self):
        import tempfile
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from PIL import Image
        from recette.views import _image_uri

        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            contenu = BytesIO()
            Image.new('RGB', (10, 10), 'red').save(contenu, 'JPEG')
            self.importee.image = SimpleUploadedFile('photo.jpg', contenu.getvalue(), content_type='image/jpeg')
            self.importee.save()
            uri = _image_uri(self.importee)
            self.assertTrue(uri.startswith('file://'), uri)
            self.assertTrue(uri.endswith('.jpg'))

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


class ValidationParametresTests(TestCase):
    """Paramètres invalides : erreur 400 explicite, jamais d'erreur 500."""

    def setUp(self):
        self.chef = User.objects.create_user(email='chef@example.com', password='motdepasse123', is_active=True)
        self.type = TypeRecette.objects.create(user=self.chef, type='Plat')
        self.client = APIClient()
        self.client.force_authenticate(self.chef)

    def test_identifiants_non_entiers(self):
        for url in ('/api/recette/?userId=abc', '/api/recette/?typeRecetteId=abc', '/api/recette/ingredient/?recetteId=abc',
                    '/api/recette/preparation/?recetteId=abc', '/api/tag/?userId=abc', '/api/tag/?recetteId=x',
                    '/api/typeRecette/?userId=abc'):
            self.assertEqual(self.client.get(url).status_code, 400, url)

    def test_portion_au_moins_une(self):
        res = self.client.post('/api/recette/', {'titre': 'Soupe', 'portion': 0, 'typeRecette': self.type.id}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('portion', res.data)

    def test_type_de_recette_long(self):
        res = self.client.post('/api/typeRecette/', {'type': 'Accompagnement'}, format='json')
        self.assertEqual(res.status_code, 201, res.data)


class EnregistrementRecetteTests(TestCase):
    """POST /recette/enregistrer/ et PUT /recette/<id>/enregistrer/ : tout ou rien."""

    def setUp(self):
        from tag.models import Tag
        self.user = User.objects.create_user(email='chef@example.com', password='motdepasse123', is_active=True)
        self.type = TypeRecette.objects.create(user=self.user, type='Plat')
        self.tag = Tag.objects.create(user=self.user, tag='Été', opacite=255, red=1, green=2, blue=3)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def donnees(self, **autres):
        return {
            'recette': {'titre': 'Crêpes', 'portion': 4, 'typeRecette': self.type.id},
            'ingredients': [{'isSection': False, 'nom': 'farine', 'quantite': '250'}, {'isSection': False, 'nom': 'lait', 'quantite': '50'}],
            'etapes': [{'isSection': False, 'description': 'Mélanger'}],
            'tags': [self.tag.id],
            **autres,
        }

    def creer(self):
        res = self.client.post('/api/recette/enregistrer/', self.donnees(), format='json')
        self.assertEqual(res.status_code, 201, res.data)
        return res.data

    def test_creation_complete(self):
        data = self.creer()
        recette = Recette.objects.get(pk=data['recette']['id'])
        self.assertEqual(list(recette.ingredient_set.order_by('noOrdre').values_list('nom', 'noOrdre')), [('farine', 0), ('lait', 1)])
        self.assertEqual(recette.preparation_set.count(), 1)
        self.assertEqual(data['tags'], [self.tag.id])

    def test_modification_supprime_reordonne_adapte(self):
        data = self.creer()
        farine, lait = data['ingredients']
        res = self.client.put(f"/api/recette/{data['recette']['id']}/enregistrer/", self.donnees(
            recette={'titre': 'Crêpes', 'portion': 8, 'typeRecette': self.type.id},
            # lait passe devant, farine supprimée, œufs ajoutés
            ingredients=[{'id': lait['id'], 'isSection': False, 'nom': 'lait', 'quantite': '50'}, {'isSection': False, 'nom': 'œufs', 'quantite': '3'}],
            etapes=[], tags=[], adapteQuantity=True,
        ), format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual([(i['nom'], i['noOrdre'], i['quantite']) for i in res.data['ingredients']], [('lait', 0, '100.00'), ('œufs', 1, '6.00')])
        self.assertEqual((res.data['etapes'], res.data['tags']), ([], []))
        self.assertFalse(Recette.objects.get(pk=data['recette']['id']).ingredient_set.filter(id=farine['id']).exists())

    def test_tags_null_inchanges(self):
        data = self.creer()
        res = self.client.put(f"/api/recette/{data['recette']['id']}/enregistrer/", self.donnees(tags=None), format='json')
        self.assertEqual(res.data['tags'], [self.tag.id])

    def test_erreur_annule_tout(self):
        data = self.creer()
        url = f"/api/recette/{data['recette']['id']}/enregistrer/"
        # étapes valides, mais tag d'un autre utilisateur : rien ne doit être enregistré
        res = self.client.put(url, self.donnees(recette={'titre': 'Gaufres'}, etapes=[], tags=[999]), format='json')
        self.assertEqual(res.status_code, 400)
        recette = Recette.objects.get(pk=data['recette']['id'])
        self.assertEqual((recette.titre, recette.preparation_set.count()), ('Crêpes', 1))

    def test_creation_titre_deja_pris_ne_cree_rien(self):
        self.creer()
        res = self.client.post('/api/recette/enregistrer/', self.donnees(), format='json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Recette.objects.count(), 1)

    def test_ligne_d_une_autre_recette_refusee(self):
        a = self.creer()
        b = self.client.post('/api/recette/enregistrer/', self.donnees(recette={'titre': 'Gaufres', 'portion': 2, 'typeRecette': self.type.id}), format='json').data
        intrus = a['ingredients'][0]['id']
        res = self.client.put(f"/api/recette/{b['recette']['id']}/enregistrer/",
                              self.donnees(ingredients=[{'id': intrus, 'isSection': False, 'nom': 'x'}]), format='json')
        self.assertEqual(res.status_code, 400)
        self.assertTrue(Recette.objects.get(pk=a['recette']['id']).ingredient_set.filter(id=intrus).exists())

    def test_recette_d_un_autre_utilisateur_refusee(self):
        data = self.creer()
        autre = APIClient()
        autre.force_authenticate(User.objects.create_user(email='autre@example.com', password='motdepasse123', is_active=True))
        res = autre.put(f"/api/recette/{data['recette']['id']}/enregistrer/", self.donnees(), format='json')
        self.assertEqual(res.status_code, 403)

    def test_multipart_donnees_json(self):
        import json
        res = self.client.post('/api/recette/enregistrer/', {'donnees': json.dumps(self.donnees())}, format='multipart')
        self.assertEqual(res.status_code, 201, res.data)


DESCRIPTION_STRUCTUREE = """Crêpes moelleuses 🥞 pour 6 personnes
Préparation : 10 min
Cuisson : 1 h 5
Ingrédients :
- 250 g de farine
- 3 oeufs
• 50 cl de lait
Pour la garniture :
- sucre
Étapes :
1️⃣ Mélanger la farine et les oeufs.
2) Ajouter le lait petit à petit.
#crepes #recette @chef"""

DESCRIPTION_UNE_LIGNE = ("pommes de terre caramélisées au miel  Pour 2-3 personnes  Ingrédients : - 300 g de petites pommes de terre "
                         "- Huile de sésame - 3 gousses d'ail -250ml Eau - 2 cas de miel Miel - 80ml de Sauce soja "
                         "Instructions : 1. Laver les pommes de terre. 2. Ajouter l'ail. 3. Verser le mélange.")

DESCRIPTION_EN_PROSE = "Trop bonnes ces crêpes 😍 il te faut de la farine, des oeufs et du lait, tu mélanges et c'est prêt ! #crepes"


class DescriptionAvecRecetteTests(SimpleTestCase):
    """Décide seulement s'il faut télécharger la vidéo : Claude lit la description dans tous les cas."""

    def test_recette_visible(self):
        self.assertTrue(import_video.description_avec_recette(DESCRIPTION_STRUCTUREE))
        self.assertTrue(import_video.description_avec_recette(DESCRIPTION_UNE_LIGNE))

    def test_pas_de_recette(self):
        self.assertFalse(import_video.description_avec_recette(DESCRIPTION_EN_PROSE))
        self.assertFalse(import_video.description_avec_recette("🌟🍝BEST PASTA🍝🌟 " + "#recette #recettefacile #pasta " * 5))


@override_settings(ANTHROPIC_API_KEY='cle-de-test')
class ImportVideoTests(TestCase):
    """Import TikTok : lecture de la vidéo et IA simulées (ni réseau ni API en test)."""

    REPONSE_IA = {
        'titre': 'Crêpes', 'portion': 4, 'tempsPreparation': 10, 'tempsCuisson': None,
        'ingredients': ['250 g de farine', '3 oeufs', ''], 'etapes': ['Mélanger la farine et les oeufs.', 'Ajouter le lait.'],
    }

    def setUp(self):
        self.user = User.objects.create_user(email='chef@example.com', password='motdepasse123', is_active=True)
        self.type = TypeRecette.objects.create(user=self.user, type='Plat')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        Unite.objects.get_or_create(code='g', defaults={'description': 'gramme', 'dimension': 'masse', 'facteur': 1})
        Produit.objects.get_or_create(nom='farine')

    def lancer(self, url='https://vm.tiktok.com/ZMabc123/'):
        with patch('recette.import_video._adresse_publique', return_value=True):
            res = self.client.post('/api/recette/import-url/', {'url': url, 'typeRecette': self.type.id, 'importerImage': False}, format='json')
        self.assertEqual(res.status_code, 202, res.data)
        return res.data['importVideo']['id']

    def suivre(self, import_id):
        res = self.client.get(f'/api/recette/import-video/{import_id}/')
        self.assertEqual(res.status_code, 200, res.data)
        return res.data

    def importer(self, description, **patch_ia):
        import_id = self.lancer()
        self.assertEqual(self.suivre(import_id)['statut'], 'attente')
        video = {'titre': 'Les meilleures crêpes 🥞 #recette', 'description': description, 'miniature': None}
        with patch('recette.import_video.lire_video', return_value=video), \
             patch('recette.import_video.media_disponible', return_value=True), \
             patch('recette.import_video.analyser_video', return_value=('Je vous note les ingrédients', [b'jpeg'])) as media, \
             patch('recette.import_video.structurer_avec_claude', **patch_ia) as ia:
            import_video.traiter(import_id)
        self.media = media
        return self.suivre(import_id), ia

    def test_description_toujours_lue_par_l_ia(self):
        suivi, ia = self.importer(DESCRIPTION_STRUCTUREE, return_value=self.REPONSE_IA)
        self.assertEqual(suivi['statut'], 'termine', suivi)
        self.assertEqual(ia.call_args.args, ('Les meilleures crêpes 🥞 #recette', DESCRIPTION_STRUCTUREE))
        self.media.assert_not_called()
        recette = Recette.objects.get(pk=suivi['recette'])
        self.assertEqual((recette.titre, recette.source), ('Crêpes', 'https://vm.tiktok.com/ZMabc123/'))
        farine = recette.ingredient_set.get(noOrdre=0)
        self.assertEqual((farine.quantite, farine.unite.code, farine.produit.nom), (250, 'g', 'farine'))

    def test_prose_confiee_a_l_ia(self):
        suivi, ia = self.importer(DESCRIPTION_EN_PROSE, return_value=self.REPONSE_IA)
        self.assertEqual(suivi['statut'], 'termine', suivi)
        # voix et images de la vidéo transmises à l'IA
        self.assertEqual(ia.call_args.args[2:], ('Je vous note les ingrédients', [b'jpeg']))
        recette = Recette.objects.get(pk=suivi['recette'])
        self.assertEqual((recette.titre, recette.tempsPreparation, recette.ingredient_set.count(), recette.preparation_set.count()), ('Crêpes', 10, 2, 2))

    def test_recette_dans_la_description_sans_telecharger_la_video(self):
        suivi, ia = self.importer(DESCRIPTION_UNE_LIGNE, return_value=self.REPONSE_IA)
        self.assertEqual(suivi['statut'], 'termine', suivi)
        self.assertEqual(len(ia.call_args.args), 2)  # titre et description seulement
        self.media.assert_not_called()

    def test_description_insuffisante_puis_video(self):
        vide = {**self.REPONSE_IA, 'ingredients': ['sel'], 'etapes': []}
        suivi, ia = self.importer(DESCRIPTION_UNE_LIGNE, side_effect=[vide, self.REPONSE_IA])
        self.assertEqual(suivi['statut'], 'termine', suivi)
        self.assertEqual(ia.call_count, 2)
        self.media.assert_called_once()

    def test_ia_indisponible(self):
        suivi, _ = self.importer(DESCRIPTION_EN_PROSE, side_effect=ClaudeIndisponible('crédit épuisé'))
        self.assertEqual((suivi['statut'], suivi['recette']), ('erreur', None))
        self.assertIn('momentanément indisponible', suivi['erreur'])
        self.assertEqual(Recette.objects.count(), 0)

    @override_settings(ANTHROPIC_API_KEY='')
    def test_sans_cle_import_desactive(self):
        with patch('recette.import_video._adresse_publique', return_value=True):
            res = self.client.post('/api/recette/import-url/', {'url': 'https://www.tiktok.com/@chef/video/1', 'typeRecette': self.type.id}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertFalse(ImportVideo.objects.exists())
        self.assertNotIn('tiktok.com', [s['domaine'] for s in self.client.get('/api/recette/import-sites/').data])

    def test_ia_en_panne_ne_lit_pas_la_video(self):
        EtatClaude.objects.create(pk=1, enPanne=True, derniereTentative=timezone.now())
        import_id = self.lancer()
        with patch('recette.import_video.lire_video') as lire:
            import_video.traiter(import_id)
        lire.assert_not_called()
        self.assertIn('momentanément indisponible', self.suivre(import_id)['erreur'])

    def test_description_sans_recette(self):
        suivi, _ = self.importer(DESCRIPTION_EN_PROSE, return_value={**self.REPONSE_IA, 'ingredients': [], 'etapes': []})
        self.assertEqual(suivi['statut'], 'erreur')
        self.assertIn('Aucune recette', suivi['erreur'])

    def test_import_interrompu_signale(self):
        import_id = self.lancer()
        ImportVideo.objects.filter(pk=import_id).update(creeLe=timezone.now() - timedelta(hours=1))
        self.assertEqual(self.suivre(import_id)['statut'], 'erreur')

    def test_suivi_reserve_a_son_auteur(self):
        import_id = self.lancer()
        autre = APIClient()
        autre.force_authenticate(User.objects.create_user(email='autre@example.com', password='motdepasse123', is_active=True))
        self.assertEqual(autre.get(f'/api/recette/import-video/{import_id}/').status_code, 404)

    def test_site_tiktok_liste(self):
        domaines = [s['domaine'] for s in self.client.get('/api/recette/import-sites/').data]
        self.assertIn('tiktok.com', domaines)

    def test_donnees_ia_nettoyees(self):
        video = {'titre': 'Les meilleures crêpes', 'description': '', 'miniature': None}
        donnees = import_video.donnees_recette(video, {'titre': '', 'portion': 0, 'tempsPreparation': -5, 'tempsCuisson': True,
                                                       'ingredients': 'pas une liste', 'etapes': ['  <b>Cuire</b>  ']})
        self.assertEqual(donnees['titre'], 'Les meilleures crêpes')
        self.assertEqual((donnees['portion'], donnees['tempsPreparation'], donnees['tempsCuisson']), (4, None, None))
        self.assertEqual((donnees['ingredients'], donnees['etapes']), ([], [(False, 'Cuire')]))


def _erreur_api(classe, status):
    reponse = httpx.Response(status, request=httpx.Request('POST', 'https://api.anthropic.com/v1/messages'))
    return classe(f"erreur {status}", response=reponse, body=None)


def _reponse_ia(contenu, tokens_entree=20_000, tokens_sortie=1_000, modele='claude-haiku-5-5'):
    return Mock(stop_reason='end_turn', model=modele, content=[Mock(type='text', text=json.dumps(contenu))],
                usage=Mock(input_tokens=tokens_entree, output_tokens=tokens_sortie))


@override_settings(ANTHROPIC_API_KEY='cle-de-test', ALERTE_EMAIL='admin@example.com')
class SurveillanceClaudeTests(TestCase):
    """Pannes de l'API Claude : alerte unique, pause entre les tentatives, rétablissement."""

    def structurer(self, effet):
        with patch('recette.import_ia._client') as client:
            client.return_value.messages.create.side_effect = effet if isinstance(effet, (Exception, list)) else None
            if not isinstance(effet, (Exception, list)):
                client.return_value.messages.create.return_value = effet
            try:
                return import_ia.structurer_avec_claude('Crêpes', 'description')
            finally:
                self.appels = client.return_value.messages.create.call_count

    def test_succes(self):
        self.assertEqual(self.structurer(_reponse_ia({'titre': 'Crêpes'})), {'titre': 'Crêpes'})
        self.assertFalse(EtatClaude.obtenir().enPanne)

    def test_credit_epuise_alerte_une_seule_fois(self):
        with self.assertRaises(ClaudeIndisponible):
            self.structurer(_erreur_api(anthropic.PaymentRequiredError, 402))
        etat = EtatClaude.obtenir()
        self.assertTrue(etat.enPanne)
        self.assertIn('402', etat.raison)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['admin@example.com'])

        # pendant la panne : l'API n'est pas rappelée avant 15 minutes, pas de deuxième e-mail
        with self.assertRaises(ClaudeIndisponible):
            self.structurer(_reponse_ia({'titre': 'Crêpes'}))
        self.assertEqual(self.appels, 0)
        self.assertEqual(len(mail.outbox), 1)

    def test_retablissement(self):
        with self.assertRaises(ClaudeIndisponible):
            self.structurer(_erreur_api(anthropic.AuthenticationError, 401))
        EtatClaude.objects.update(derniereTentative=timezone.now() - timedelta(minutes=16))
        self.structurer(_reponse_ia({'titre': 'Crêpes'}))
        self.assertFalse(EtatClaude.obtenir().enPanne)
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('refonctionne', mail.outbox[1].subject)

    def test_erreurs_passageres_repetees(self):
        for _ in range(import_ia.SEUIL_ECHECS_TEMPORAIRES - 1):
            with self.assertRaises(ClaudeIndisponible):
                self.structurer(_erreur_api(anthropic.OverloadedError, 529))
        self.assertFalse(EtatClaude.obtenir().enPanne)
        self.assertEqual(len(mail.outbox), 0)
        with self.assertRaises(ClaudeIndisponible):
            self.structurer(anthropic.APIConnectionError(request=httpx.Request('POST', 'https://api.anthropic.com')))
        self.assertTrue(EtatClaude.obtenir().enPanne)
        self.assertEqual(len(mail.outbox), 1)

    def test_un_succes_remet_le_compteur_a_zero(self):
        with self.assertRaises(ClaudeIndisponible):
            self.structurer(_erreur_api(anthropic.OverloadedError, 529))
        self.structurer(_reponse_ia({}))
        self.assertEqual(EtatClaude.obtenir().echecsTemporaires, 0)

    def test_verification_manuelle_pendant_la_panne(self):
        with self.assertRaises(ClaudeIndisponible):
            self.structurer(_erreur_api(anthropic.PaymentRequiredError, 402))
        with patch('recette.import_ia._client') as client:
            client.return_value.messages.create.return_value = _reponse_ia({})
            self.assertEqual(import_ia.verifier_maintenant(), (True, "L'API Claude répond."))
        self.assertFalse(EtatClaude.obtenir().enPanne)

    def test_images_et_transcription_envoyees(self):
        with patch('recette.import_ia._client') as client:
            client.return_value.messages.create.return_value = _reponse_ia({})
            import_ia.structurer_avec_claude('Crêpes', 'desc', 'il te faut', [b'image1', b'image2'])
            contenu = client.return_value.messages.create.call_args.kwargs['messages'][0]['content']
        self.assertEqual([bloc['type'] for bloc in contenu], ['image', 'image', 'text'])
        self.assertEqual(contenu[0]['source']['data'], 'aW1hZ2Ux')
        self.assertIn('<transcription>\nil te faut\n</transcription>', contenu[2]['text'])

    def test_journal_succes_avec_cout(self):
        tache = ImportVideo.objects.create(user=User.objects.create_user(email='j@example.com', password='motdepasse123', is_active=True),
                                           url='https://www.tiktok.com/@a/video/1', typeRecette=TypeRecette.objects.create(
                                               user=User.objects.get(email='j@example.com'), type='Plat'))
        with patch('recette.import_ia._client') as client:
            client.return_value.messages.create.return_value = _reponse_ia({'titre': 'Crêpes'})
            import_ia.structurer_avec_claude('Crêpes', 'la description', 'la voix', [b'i1', b'i2'], tache=tache)
        appel = AppelIA.objects.get()
        self.assertEqual((appel.etape, appel.importVideo, appel.user, appel.nbImages, appel.statut), ('video', tache, tache.user, 2, 'succes'))
        # 20 000 x 0,10 $ + 1 000 x 0,50 $ par million = 0,0025 $
        self.assertEqual((appel.tokensEntree, appel.tokensSortie, appel.cout), (20_000, 1_000, Decimal('0.0025')))
        self.assertIn('<transcription>\nla voix', appel.entree)
        self.assertEqual(json.loads(appel.reponse), {'titre': 'Crêpes'})

    def test_journal_erreur_sans_cout(self):
        with self.assertRaises(ClaudeIndisponible):
            self.structurer(_erreur_api(anthropic.PaymentRequiredError, 402))
        appel = AppelIA.objects.get()
        self.assertEqual((appel.etape, appel.statut, appel.cout), ('description', 'erreur', 0))
        self.assertIn('402', appel.erreur)

    def test_cout(self):
        self.assertEqual(import_ia._cout('claude-sonnet-5-5', 1_000_000, 100_000), Decimal('3'))
        self.assertEqual(import_ia._cout('claude-haiku-5-5', 200_000, 0), Decimal('0.1'))  # tarif long contexte
        self.assertIsNone(import_ia._cout('modele-inconnu', 1000, 1000))

    def test_admin_totaux(self):
        self.structurer(_reponse_ia({}))
        self.structurer(_reponse_ia({}))
        admin = User.objects.create_superuser(email='admin@example.com', password='motdepasse123')
        self.client.force_login(admin)
        res = self.client.get('/admin/recette/appelia/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '2 appels')
        self.assertContains(res, '0,0050 $')  # total
        self.assertContains(res, '0,0025 $')  # colonne coût

    @override_settings(ANTHROPIC_API_KEY='')
    def test_sans_cle(self):
        with self.assertRaises(ClaudeIndisponible):
            import_ia.structurer_avec_claude('Crêpes', 'description')
        self.assertFalse(EtatClaude.objects.exists())


class ReferentielProduitsTests(TestCase):
    """Synonymes, produits à vérifier, recherche, déterminant, ingrédients sans produit (admin)."""

    def setUp(self):
        self.oignon = Produit.objects.create(nom='oignon', nomPluriel='oignons')
        self.poireau = Produit.objects.create(nom='poireau', nomPluriel='poireaux')
        Synonyme.objects.create(texte='poireau émincé surgelé', produit=self.poireau)
        Produit.objects.create(nom='topinambour', statut=Produit.Statut.A_VERIFIER, source=Produit.Source.IA)
        self.user = User.objects.create_superuser(email='admin@example.com', password='motdepasse123')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_reconnaissance(self):
        analyseur = AnalyseurIngredients()
        self.assertEqual(analyseur.analyser('2 gros oignons émincés')[2:], (self.oignon, None, 'gros, émincés'))
        self.assertEqual(analyseur.analyser('1 Poireau émincé surgelé')[2], self.poireau)
        # produit à vérifier : pas encore utilisé
        self.assertEqual(analyseur.analyser('2 topinambours')[2:4], (None, 'topinambours'))

    def test_recherche_par_synonyme_et_validation(self):
        noms = lambda q: [p['nom'] for p in self.client.get('/api/recette/produit/', {'searchProduit': q}).data]
        self.assertEqual(noms('surgelé'), ['poireau'])
        self.assertEqual(noms('topinam'), [])

    def test_determinant_et_pluriel_automatiques(self):
        self.assertEqual((Produit.objects.create(nom='échalote').determinant, Produit.objects.create(nom='sel').determinant), ("d'", 'de'))
        self.assertEqual(Produit.objects.create(nom='riz').nomPluriel, 'riz')
        self.assertEqual(Produit.objects.create(nom='haricot', determinant='de').determinant, 'de')  # h aspiré corrigé à la main

    def test_ingredient_sans_produit_associe_et_appris(self):
        type_recette = TypeRecette.objects.create(user=self.user, type='Plat')
        recette = Recette.objects.create(user=self.user, typeRecette=type_recette, titre='Soupe', portion=2)
        ingredient = Ingredient.objects.create(recette=recette, noOrdre=0, quantite=2, nom='Poireaux bio')
        self.client.force_login(self.user)
        page = self.client.get('/admin/recette/ingredientsansproduit/')
        self.assertContains(page, 'Poireaux bio')
        reponse = self.client.post('/admin/recette/ingredientsansproduit/', {
            'form-TOTAL_FORMS': 1, 'form-INITIAL_FORMS': 1, 'form-0-id': ingredient.id, 'form-0-produit': self.poireau.id, '_save': 'Enregistrer',
        })
        self.assertEqual(reponse.status_code, 302)
        ingredient.refresh_from_db()
        self.assertEqual((ingredient.produit, ingredient.nom, ingredient.quantite), (self.poireau, 'Poireaux bio', 2))
        self.assertEqual(Synonyme.objects.get(cle='poireaux bio').produit, self.poireau)
        self.assertEqual(AnalyseurIngredients().analyser('3 poireaux bio')[2], self.poireau)

    def test_pages_admin(self):
        self.client.force_login(self.user)
        Equivalence.objects.create(produit=self.oignon, quantite=1, quantiteCible=150, uniteCible=Unite.objects.get_or_create(
            code='g', defaults={'description': 'gramme', 'dimension': 'masse', 'facteur': 1})[0])
        for url in ('/admin/recette/produit/', f'/admin/recette/produit/{self.oignon.id}/change/', '/admin/recette/produit/?statut__exact=a_verifier'):
            self.assertEqual(self.client.get(url).status_code, 200, url)
