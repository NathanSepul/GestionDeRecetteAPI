"""
Nettoyage de la liste des produits : fautes de frappe, doublons, unités encore cachées dans les noms,
et produits de base (ce qu'on achète réellement : "ail haché" -> "ail").

Comme la 0030, prévu pour la production : tout se fait par nom (jamais par id),
un produit absent est ignoré, un produit cible est réutilisé s'il existe déjà.
"""
from django.db import migrations


# ancien nom -> (nouveau nom, pluriel). Si le nouveau nom existe déjà, les deux produits sont fusionnés.
RENOMMAGES = [
    ('roblochon', 'reblochon', 'reblochons'),
    ('marget de canard', 'magret de canard', 'magrets de canard'),
    ('bourrata', 'burrata', 'burratas'),
    ('haché au fenouille', 'haché au fenouil', 'haché au fenouil'),
    ('garam massala', 'garam masala', 'garam masala'),
    ('kambu', 'kombu', 'kombu'),
    ('mirine', 'mirin', 'mirin'),
    ('crevette roses', 'crevette rose', 'crevettes roses'),
    ('sel et poive', 'sel et poivre', 'sel et poivre'),
    ('bacon (coupé en lanières)', 'bacon', 'bacon'),
    ('figue fraiche pour la décoration', 'figue fraîche', 'figues fraîches'),
    ('zeste d’un citron non traité', 'zeste de citron', 'zestes de citron'),
    ("zeste d'un citron non traité", 'zeste de citron', 'zestes de citron'),
    ('grosse pomme', 'pomme', 'pommes'),
]

# doublons : ancien -> produit conservé (l'unité des ingrédients ne change pas)
FUSIONS = [
    ('bouillon de légume', 'bouillon de légumes'),
    ('herbe de provence', 'herbes de provence'),
    ('harrissa', 'harissa'),
    ('farine de blé', 'farine'),
    ('fécule de maïs', 'maïzena'),
    ("mélange d'épices itialien", 'épices italiennes'),
    ('sauce nuoc-man', 'sauce de poisson'),
    ('baking powder', 'levure chimique'),
    ('levure', 'levure chimique'),
    ('huile végétale', 'huile neutre'),
    ('coriandre', 'coriandre fraîche'),
    ('sucre brun', 'sucre roux'),
]

# code, pluriel, description
NOUVELLES_UNITES = [
    ('dosette', 'dosettes', 'Dosette'),
    ('goutte', 'gouttes', 'Goutte'),
]

# ancien produit -> (produit cible, unité, pluriel du produit cible s'il faut le créer)
UNITES_DANS_LE_NOM = [
    ('dosette de filaments de safran', 'safran', 'dosette', 'safran'),
    ("goutte d'extrait d'amande", "extrait d'amande", 'goutte', "extrait d'amande"),
]

# produit -> produit de base (ce qu'on achète). Les variétés (oignon rouge, citron vert...) n'ont pas de base.
BASES = [
    ("blanc d'œuf", 'œuf'),
    ('jus de citrons', 'citron'),
    ('zeste de citron', 'citron'),
    ('jus de citron vert', 'citron vert'),
    ('jus de gingembre', 'gingembre'),
    ('amande effilée', 'amande'),
    ('pistache pelées non salée', 'pistache'),
    ('quelques feuilles de basilic', 'basilic'),
    ('plant de ciboulette', 'ciboulette'),
    ('plant de persil plat', 'persil plat'),
    ('petit poireau', 'poireau'),
    ('tomates cerises de différentes couleurs', 'tomate cerise'),
    ('bébé pak-choy', 'pak-choï'),
    ('huile neutre pour friture', 'huile neutre'),
    ('harissa en tube', 'harissa'),
    ('beurre doux', 'beurre'),
    ('beurre doux fondu', 'beurre'),
]


def _determinant(nom):
    return "d'" if nom[:1].lower() in 'aeiouéèêàâîôûœ' else 'de'


def _trouver(Produit, nom):
    return Produit.objects.filter(nom__iexact=nom).first()


def _fusionner(Produit, Ingredient, ancien, nouveau, unite=None):
    """Repointe ingrédients et produitDeBase de l'ancien produit vers le nouveau, puis supprime l'ancien s'il n'est plus utilisé."""
    if ancien.pk == nouveau.pk:
        return 0

    ingredients = Ingredient.objects.filter(produit=ancien)
    if unite is None:
        nb = ingredients.update(produit=nouveau)
    else:
        nb = ingredients.filter(unite__isnull=True).update(produit=nouveau, unite=unite)

    Produit.objects.filter(produitDeBase=ancien).exclude(pk=nouveau.pk).update(produitDeBase=nouveau)
    if nouveau.produitDeBase_id == ancien.pk:
        nouveau.produitDeBase = None
        nouveau.save(update_fields=['produitDeBase'])

    if not Ingredient.objects.filter(produit=ancien).exists():
        ancien.delete()
    else:
        print(f"\n  ! '{ancien.nom}' conservé : des ingrédients ont déjà une unité")
    return nb


def nettoyer_produits(apps, schema_editor):
    Unite = apps.get_model('recette', 'Unite')
    Produit = apps.get_model('recette', 'Produit')
    Ingredient = apps.get_model('recette', 'Ingredient')
    total = 0

    for nom_ancien, nom_nouveau, pluriel in RENOMMAGES:
        ancien = _trouver(Produit, nom_ancien)
        if ancien is None:
            continue
        existant = _trouver(Produit, nom_nouveau)
        if existant and existant.pk != ancien.pk:
            total += _fusionner(Produit, Ingredient, ancien, existant)
        else:
            ancien.nom, ancien.nomPluriel = nom_nouveau, pluriel
            ancien.save(update_fields=['nom', 'nomPluriel'])

    for nom_ancien, nom_cible in FUSIONS:
        ancien, cible = _trouver(Produit, nom_ancien), _trouver(Produit, nom_cible)
        if ancien and cible:
            total += _fusionner(Produit, Ingredient, ancien, cible)

    unites = {}
    for code, pluriel, description in NOUVELLES_UNITES:
        unites[code], _ = Unite.objects.get_or_create(
            code=code, defaults={'pluriel': pluriel, 'description': description, 'dimension': 'vague'},
        )

    for nom_ancien, nom_cible, code_unite, pluriel in UNITES_DANS_LE_NOM:
        ancien = _trouver(Produit, nom_ancien)
        if ancien is None:
            continue
        cible = _trouver(Produit, nom_cible) or Produit.objects.create(
            nom=nom_cible, nomPluriel=pluriel, determinant=_determinant(nom_cible),
        )
        total += _fusionner(Produit, Ingredient, ancien, cible, unites[code_unite])

    nb_bases = 0
    for nom_produit, nom_base in BASES:
        produit, base = _trouver(Produit, nom_produit), _trouver(Produit, nom_base)
        if produit and base and produit.pk != base.pk and produit.produitDeBase_id != base.pk:
            produit.produitDeBase = base
            produit.save(update_fields=['produitDeBase'])
            nb_bases += 1

    print(f"\n  {total} ingrédient(s) repointé(s), {nb_bases} produit(s) de base renseigné(s)")


class Migration(migrations.Migration):

    dependencies = [
        ('recette', '0030_unites_extraites_des_produits'),
    ]

    operations = [
        # pas de retour arrière des données : faire une sauvegarde de la base avant d'appliquer en production
        migrations.RunPython(nettoyer_produits, migrations.RunPython.noop),
    ]
