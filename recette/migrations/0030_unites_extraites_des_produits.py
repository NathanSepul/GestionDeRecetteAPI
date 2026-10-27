"""
Sort les unités cachées dans les noms de produits : "gousse d'ail" devient produit "ail" + unité "gousse".
Ainsi "2 gousses d'ail" et "10 g d'ail" portent sur le même produit dans la liste de courses.

Prévu pour tourner aussi en production : tout se fait par nom (jamais par id),
un produit absent est ignoré, un produit cible est réutilisé s'il existe déjà.
Un ingrédient qui a déjà une unité n'est pas touché (on ne remplacerait pas "1 cs" par "gousse").
"""
from decimal import Decimal
from django.db import migrations


# code, pluriel, description, dimension, facteur
NOUVELLES_UNITES = [
    ('gousse', 'gousses', 'Gousse', 'vague', None),
    ('branche', 'branches', 'Branche', 'vague', None),
    ('brin', 'brins', 'Brin', 'vague', None),
    ('botte', 'bottes', 'Botte', 'vague', None),
    ('bouquet', 'bouquets', 'Bouquet', 'vague', None),
    ('tranche', 'tranches', 'Tranche', 'vague', None),
    ('feuille', 'feuilles', 'Feuille', 'vague', None),
    ('poignée', 'poignées', 'Poignée', 'vague', None),
    ('bâton', 'bâtons', 'Bâton', 'vague', None),
    ('sachet', 'sachets', 'Sachet', 'vague', None),
    ('tasse', 'tasses', 'Tasse (250 ml)', 'volume', Decimal('250')),
]

# code actuel -> (nouveau code, pluriel, description)
CORRECTIONS_UNITES = {
    'pc': ('pincée', 'pincées', 'Pincée'),
    'ml': ('ml', '', 'Millilitre'),
    'kg': ('kg', '', 'Kilogramme'),
    'cm': ('cm', '', 'Centimètre'),
}

# ancien produit -> (produit cible, unité, pluriel du produit cible s'il faut le créer)
PRODUITS = [
    ("gousse d'ail", 'ail', 'gousse', 'ail'),
    ('gousse de vanille', 'vanille', 'gousse', 'vanille'),
    ('pincée de sel', 'sel', 'pincée', 'sel'),
    ('pincée de paprika', 'paprika', 'pincée', 'paprika'),
    ('pincée de canelle', 'cannelle', 'pincée', 'cannelle'),
    ('pincée de thym', 'thym', 'pincée', 'thym'),
    ('pincée de céleri', 'céleri', 'pincée', 'céleri'),
    ("tasse d'eau", 'eau', 'tasse', 'eau'),
    ('tasse de bouillon de poule', 'bouillon de poule', 'tasse', 'bouillon de poule'),
    ('tasse de farine fermantante', 'farine fermentante', 'tasse', 'farine fermentante'),
    ('tasse de riz basmati lavé', 'riz basmati', 'tasse', 'riz basmati'),
    ('tasse de sucre fin', 'sucre fin', 'tasse', 'sucre fin'),
    ('tasse de yaourt', 'yaourt', 'tasse', 'yaourts'),
    ('branche de thym', 'thym', 'branche', 'thym'),
    ('branche de basilic', 'basilic', 'branche', 'basilic'),
    ('branche de coriandre', 'coriandre', 'branche', 'coriandre'),
    ('branche de menthe fraîche', 'menthe fraîche', 'branche', 'menthe fraîche'),
    ('brin de ciboulette', 'ciboulette', 'brin', 'ciboulette'),
    ('brin de persil plat', 'persil plat', 'brin', 'persil plat'),
    ('botte de cresson', 'cresson', 'botte', 'cresson'),
    ('botte de poireaux', 'poireau', 'botte', 'poireaux'),
    ('botte de blanc de poireaux', 'poireau', 'botte', 'poireaux'),
    ('bouquet de coriandre', 'coriandre', 'bouquet', 'coriandre'),
    ('petit bouquet de basilic', 'basilic', 'bouquet', 'basilic'),
    ('feuille de basilic', 'basilic', 'feuille', 'basilic'),
    ('feuille de laurier', 'laurier', 'feuille', 'laurier'),
    ('feuille de menthe', 'menthe fraîche', 'feuille', 'menthe fraîche'),
    ("tranche d'ananas", 'ananas', 'tranche', 'ananas'),
    ('tranche de carpaccio de bœuf', 'carpaccio de bœuf', 'tranche', 'carpaccio de bœuf'),
    ('tranche de gingembre', 'gingembre', 'tranche', 'gingembre'),
    ('tranche de narutomaki', 'narutomaki', 'tranche', 'narutomaki'),
    ('poignée de basilic sacré', 'basilic sacré', 'poignée', 'basilic sacré'),
    ('poignée de noix de cajou', 'noix de cajou', 'poignée', 'noix de cajou'),
    ('bâton de cannelle', 'cannelle', 'bâton', 'cannelle'),
    ('bâton de citronelle', 'citronnelle', 'bâton', 'citronnelle'),
    ('bâton de chocolat fondant', 'chocolat fondant', 'bâton', 'chocolat fondant'),
    ("sachet d'épices pour couscous", 'épices pour couscous', 'sachet', 'épices pour couscous'),
]

# doublons / fautes de frappe : même produit, l'unité de l'ingrédient ne change pas
FUSIONS = [
    ('feuille de Wonton, coupées en 4', 'feuille de Wonton', 'feuilles de Wonton'),
    ('noix de cajoux', 'noix de cajou', 'noix de cajou'),
]


def _determinant(nom):
    return "d'" if nom[:1].lower() in 'aeiouéèêàâîôûœ' else 'de'


def _produit_cible(Produit, nom, pluriel):
    produit = Produit.objects.filter(nom__iexact=nom).first()
    if produit is None:
        produit = Produit.objects.create(nom=nom, nomPluriel=pluriel, determinant=_determinant(nom))
    return produit


def _remplacer_produit(Produit, Ingredient, nom_ancien, nouveau, unite):
    """Repointe ingrédients et produitDeBase de l'ancien produit vers le nouveau, puis supprime l'ancien s'il n'est plus utilisé."""
    ancien = Produit.objects.filter(nom__iexact=nom_ancien).first()
    if ancien is None or ancien.pk == nouveau.pk:
        return 0

    ingredients = Ingredient.objects.filter(produit=ancien)
    if unite is None:
        nb = ingredients.update(produit=nouveau)
    else:
        nb = ingredients.filter(unite__isnull=True).update(produit=nouveau, unite=unite)

    Produit.objects.filter(produitDeBase=ancien).update(produitDeBase=nouveau)

    if not Ingredient.objects.filter(produit=ancien).exists():
        ancien.delete()
    else:
        print(f"\n  ! '{ancien.nom}' conservé : des ingrédients ont déjà une unité")
    return nb


def extraire_unites(apps, schema_editor):
    Unite = apps.get_model('recette', 'Unite')
    Produit = apps.get_model('recette', 'Produit')
    Ingredient = apps.get_model('recette', 'Ingredient')

    for code, (nouveau_code, pluriel, description) in CORRECTIONS_UNITES.items():
        if nouveau_code != code and Unite.objects.filter(code=nouveau_code).exists():
            continue
        Unite.objects.filter(code=code).update(code=nouveau_code, pluriel=pluriel, description=description)

    unites = {}
    for code, pluriel, description, dimension, facteur in NOUVELLES_UNITES:
        unites[code], _ = Unite.objects.get_or_create(
            code=code,
            defaults={'pluriel': pluriel, 'description': description, 'dimension': dimension, 'facteur': facteur},
        )
    unites['pincée'] = Unite.objects.filter(code='pincée').first()

    # "u" (unité) fait doublon avec "sans unité" : ses ingrédients passent sans unité
    for unite_u in Unite.objects.filter(code='u'):
        Ingredient.objects.filter(unite=unite_u).update(unite=None)
        unite_u.delete()

    total = 0
    for nom_ancien, nom_cible, code_unite, pluriel in PRODUITS:
        unite = unites.get(code_unite)
        if unite is None or not Produit.objects.filter(nom__iexact=nom_ancien).exists():
            continue
        total += _remplacer_produit(Produit, Ingredient, nom_ancien, _produit_cible(Produit, nom_cible, pluriel), unite)

    for nom_ancien, nom_cible, pluriel in FUSIONS:
        if not Produit.objects.filter(nom__iexact=nom_ancien).exists():
            continue
        total += _remplacer_produit(Produit, Ingredient, nom_ancien, _produit_cible(Produit, nom_cible, pluriel), None)

    print(f"\n  {total} ingrédient(s) mis à jour")


class Migration(migrations.Migration):

    dependencies = [
        ('recette', '0029_unite_code_pluriel'),
    ]

    operations = [
        # pas de retour arrière des données : faire une sauvegarde de la base avant d'appliquer en production
        migrations.RunPython(extraire_unites, migrations.RunPython.noop),
    ]
