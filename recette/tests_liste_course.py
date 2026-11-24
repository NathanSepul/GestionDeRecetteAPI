"""
Liste de courses (recette/liste_course.py) : regroupements, conversions, dérivés, arrondis, tri.
Les conversions des produits sont posées par les fonctions densite(), poids_piece(), mesure() et ratio(),
pour que ces tests ne dépendent pas de la façon dont elles sont stockées.
"""
from decimal import Decimal

from django.test import TestCase

from recette.liste_course import generer_liste_course
from recette.models import Equivalence, Ingredient, Produit, Rayon, Recette, Unite
from typeRecette.models import TypeRecette
from user.models import User


def densite(produit, grammes_par_ml):
    Equivalence.objects.create(produit=produit, quantite=1, unite=Unite.objects.get(code='ml'),
                               quantiteCible=grammes_par_ml, uniteCible=Unite.objects.get(code='g'))


def poids_piece(produit, grammes):
    Equivalence.objects.create(produit=produit, quantite=1, unite=None, quantiteCible=grammes, uniteCible=Unite.objects.get(code='g'))


def mesure(produit, code_unite, quantite, code_reference=None):
    """1 <unite> du produit = quantite <reference> (None = pièces)."""
    reference = Unite.objects.get(code=code_reference) if code_reference else None
    Equivalence.objects.create(produit=produit, quantite=1, unite=Unite.objects.get(code=code_unite),
                               quantiteCible=quantite, uniteCible=reference)


def ratio(derive, quantite_base, code_unite_base, quantite_derive, code_unite_derive):
    """quantite_base <unite_base> du produit de base = quantite_derive <unite_derive> du dérivé ("1 citron = 40 ml de jus")."""
    Equivalence.objects.create(
        produit=derive, quantite=quantite_derive, unite=Unite.objects.get(code=code_unite_derive) if code_unite_derive else None,
        produitCible=derive.produitDeBase, quantiteCible=quantite_base,
        uniteCible=Unite.objects.get(code=code_unite_base) if code_unite_base else None,
    )


class ListeCourseTests(TestCase):
    def setUp(self):
        def unite(code, dimension, facteur, **autres):
            return Unite.objects.update_or_create(code=code, defaults={'description': code, 'dimension': dimension, 'facteur': facteur, **autres})[0]

        self.kg = unite('kg', 'masse', 1000)
        self.g = unite('g', 'masse', 1, borneSuperieur=1000, uniteSuperieur=self.kg)
        self.l = unite('l', 'volume', 1000)
        self.cl = unite('cl', 'volume', 10)
        self.ml = unite('ml', 'volume', 1, borneSuperieur=10, uniteSuperieur=self.cl)
        self.cs = unite('cs', 'volume', 15)
        self.cc = unite('cc', 'volume', 5)
        self.piece = unite('pièce', 'piece', 1, pluriel='pièces')
        self.gousse = unite('gousse', 'vague', None, pluriel='gousses')
        self.tranche = unite('tranche', 'vague', None, pluriel='tranches')
        self.botte = unite('botte', 'vague', None, pluriel='bottes')

        self.legumes = Rayon.objects.create(nom='Légumes test', noOrdre=1)
        self.cremerie = Rayon.objects.create(nom='Crèmerie test', noOrdre=2)
        self.epices = Rayon.objects.create(nom='Épices test', noOrdre=3)

        user = User.objects.create_user(email='chef@example.com', password='motdepasse123', is_active=True)
        self.recette = Recette.objects.create(user=user, typeRecette=TypeRecette.objects.create(user=user, type='Plat'), titre='Test', portion=4)

    def produit(self, nom, rayon=None, achat=None, base=None, placard=False):
        return Produit.objects.create(nom=nom, nomPluriel=nom + 's', rayon=rayon, uniteAchat=achat, produitDeBase=base, placard=placard)

    def ingredient(self, quantite, unite, produit=None, nom=None):
        Ingredient.objects.create(recette=self.recette, noOrdre=Ingredient.objects.count(), quantite=quantite, unite=unite,
                                  produit=produit, nom=nom)

    def liste(self, portions=4):
        return [
            (ligne['produit'].nom if ligne['produit'] else ligne['nom'], ligne['quantite'], ligne['unite'].code if ligne['unite'] else None,
             ligne['precision'])
            for ligne in generer_liste_course({self.recette: portions})
        ]

    def test_meme_dimension_additionnee(self):
        beurre = self.produit('beurre', self.cremerie, achat=self.g)
        self.ingredient(200, self.g, beurre)
        self.ingredient(Decimal('0.5'), self.kg, beurre)
        self.assertEqual(self.liste(), [('beurre', Decimal('700.00'), 'g', None)])

    def test_unite_superieure(self):
        farine = self.produit('farine', achat=self.g)
        self.ingredient(1500, self.g, farine)
        self.assertEqual(self.liste(), [('farine', Decimal('1.50'), 'kg', None)])

    def test_volume_vers_poids_par_densite(self):
        sucre = self.produit('sucre', achat=self.g)
        densite(sucre, 1)
        self.ingredient(6, self.cs, sucre)
        self.ingredient(225, self.g, sucre)
        self.assertEqual(self.liste(), [('sucre', Decimal('315.00'), 'g', None)])

    def test_poids_vers_pieces(self):
        oignon = self.produit('oignon', self.legumes, achat=self.piece)
        poids_piece(oignon, 150)
        self.ingredient(2, None, oignon)
        self.ingredient(150, self.g, oignon)
        self.assertEqual(self.liste(), [('oignon', Decimal('3'), None, None)])

    def test_pieces_arrondies_au_dessus(self):
        oignon = self.produit('oignon', achat=self.piece)
        poids_piece(oignon, 150)
        self.ingredient(200, self.g, oignon)
        self.assertEqual(self.liste(), [('oignon', Decimal('2'), None, None)])

    def test_mesure_propre_au_produit(self):
        ail = self.produit('ail', achat=self.gousse)
        mesure(ail, 'gousse', 5, 'g')
        self.ingredient(10, self.g, ail)
        self.ingredient(1, self.gousse, ail)
        self.assertEqual(self.liste(), [('ail', Decimal('3'), 'gousse', None)])

    def test_mesure_vers_unite_d_achat_en_poids(self):
        gingembre = self.produit('gingembre', achat=self.g)
        mesure(gingembre, 'tranche', 3, 'g')
        self.ingredient(2, self.tranche, gingembre)
        self.ingredient(10, self.g, gingembre)
        self.assertEqual(self.liste(), [('gingembre', Decimal('16.00'), 'g', None)])

    def test_mesure_en_pieces(self):
        poireau = self.produit('poireau', achat=self.piece)
        mesure(poireau, 'botte', 3)
        self.ingredient(1, self.botte, poireau)
        self.ingredient(1, None, poireau)
        self.assertEqual(self.liste(), [('poireau', Decimal('4'), None, None)])

    def test_derive_avec_ratio(self):
        citron = self.produit('citron', self.legumes, achat=self.piece)
        jus = self.produit('jus de citron', base=citron)
        ratio(jus, 1, None, 40, 'ml')
        self.ingredient(4, self.cl, jus)
        self.ingredient(1, None, citron)
        self.assertEqual(self.liste(), [('citron', Decimal('2'), None, 'jus de citron')])

    def test_derive_avec_ratio_arrondi(self):
        citron = self.produit('citron', achat=self.piece)
        jus = self.produit('jus de citron', base=citron)
        ratio(jus, 1, None, 40, 'ml')
        self.ingredient(5, self.cl, jus)
        self.assertEqual(self.liste(), [('citron', Decimal('2'), None, 'jus de citron')])

    def test_derive_sans_ratio_un_pour_un(self):
        oeuf = self.produit('œuf')
        jaune = self.produit("jaune d'œuf", base=oeuf)
        blanc = self.produit("blanc d'œuf", base=oeuf)
        self.ingredient(5, None, jaune)
        self.ingredient(5, None, blanc)
        # 5 jaunes + 5 blancs = 5 œufs (le plus grand des dérivés, pas la somme)
        self.assertEqual(self.liste(), [('œuf', Decimal('5'), None, "blanc d'œuf, jaune d'œuf")])

    def test_derive_ratio_en_poids(self):
        amande = self.produit('amande', achat=self.g)
        densite(amande, Decimal('0.6'))
        effilee = self.produit('amande effilée', base=amande)
        ratio(effilee, 8, 'g', 1, 'cs')
        self.ingredient(2, self.cs, effilee)
        self.assertEqual(self.liste(), [('amande', Decimal('16.00'), 'g', 'amande effilée')])

    def test_sans_quantite_ignore_si_quantite_ailleurs(self):
        sel = self.produit('sel', achat=self.g)
        self.ingredient(None, None, sel)
        self.ingredient(5, self.g, sel)
        self.assertEqual(self.liste(), [('sel', Decimal('5.00'), 'g', None)])

    def test_sans_quantite_garde(self):
        poivre = self.produit('poivre')
        self.ingredient(None, None, poivre)
        self.assertEqual(self.liste(), [('poivre', None, None, None)])

    def test_sans_unite_d_achat_familles_separees(self):
        lait = self.produit('lait')
        self.ingredient(200, self.ml, lait)
        self.ingredient(100, self.g, lait)
        self.assertEqual(sorted(self.liste(), key=str), sorted([('lait', Decimal('20.00'), 'cl', None), ('lait', Decimal('100.00'), 'g', None)], key=str))

    def test_conversion_impossible_ligne_inchangee(self):
        ail = self.produit('ail', achat=self.gousse)
        self.ingredient(10, self.g, ail)  # pas de mesure "1 gousse = 5 g"
        self.assertEqual(self.liste(), [('ail', Decimal('10.00'), 'g', None)])

    def test_portions(self):
        beurre = self.produit('beurre', achat=self.g)
        self.ingredient(100, self.g, beurre)
        self.assertEqual(self.liste(portions=6), [('beurre', Decimal('150.00'), 'g', None)])

    def test_ingredient_sans_produit(self):
        self.ingredient(1, None, nom='Sauce mystère')
        self.ingredient(2, None, nom='sauce mystère')
        self.assertEqual(self.liste(), [('Sauce mystère', Decimal('3'), None, None)])

    def test_tri_rayon_puis_placard(self):
        self.ingredient(1, None, self.produit('cumin', self.epices, placard=True))
        self.ingredient(1, None, self.produit('crème', self.cremerie))
        self.ingredient(1, None, self.produit('carotte', self.legumes))
        self.ingredient(1, None, self.produit('mystère'))
        self.assertEqual([ligne[0] for ligne in self.liste()], ['carotte', 'crème', 'mystère', 'cumin'])
