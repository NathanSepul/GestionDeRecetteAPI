"""
Conversions d'unités par produit, pour que la liste de courses additionne "6 cs de sucre" et "225 g de sucre".

1. pincée devient un volume (≈ 0,5 ml), cm devient une mesure propre au produit (cm de gingembre) ;
   une unité "pièce" sert d'unité d'achat (jamais sur un ingrédient : sans unité = pièce).
2. Les produits "préparés" (ail haché, oignon émincé, beurre mou...) disparaissent : l'ingrédient pointe vers
   le produit de base, la préparation va dans Ingredient.preparation.
3. "citron" / "citron vert" exprimés en volume sont en réalité du jus : ils pointent vers le produit jus.
4. Densité, poids d'une pièce, unité d'achat et mesures (1 gousse d'ail = 5 g...) des produits courants.

Prévu pour la production : tout se fait par nom (jamais par id), un produit absent est ignoré,
une valeur déjà saisie à la main dans l'admin n'est pas écrasée.
"""
from decimal import Decimal as D
from django.db import migrations


# produit préparé -> (produit de base, préparation)
PREPARATIONS = [
    ('ail haché', 'ail', 'haché'),
    ('oignon émincé', 'oignon', 'émincé'),
    ('oignon haché', 'oignon', 'haché'),
    ('beurre mou', 'beurre', 'mou'),
    ('beurre doux fondu', 'beurre', 'fondu'),
    ('échalote coupée finement', 'échalote', 'coupée finement'),
    ('raisin sec trempé', 'raisin sec', 'trempé'),
]

# produit exprimé en volume -> produit dérivé qu'il désigne en réalité
VOLUME_EST_UN_JUS = [
    ('citron', 'jus de citron'),
    ('citron vert', 'jus de citron vert'),
]

# produit : (densité g/ml, poids d'une pièce en g, unité d'achat)
PROPRIETES = {
    # achetés à la pièce
    'oignon': (D('0.67'), D('150'), 'pièce'),
    'citron': (None, None, 'pièce'),
    'citron vert': (None, None, 'pièce'),
    'tomate': (None, D('120'), 'pièce'),
    'poivron': (None, D('150'), 'pièce'),
    'poivron jaune': (None, D('150'), 'pièce'),
    'poivron rouge': (None, D('150'), 'pièce'),
    'poivron vert': (None, D('150'), 'pièce'),
    'panais': (None, D('150'), 'pièce'),
    'poireau': (None, D('200'), 'pièce'),
    'piment': (D('0.67'), D('10'), 'pièce'),
    'haut de cuisse de poulet': (None, D('150'), 'pièce'),
    'boule de mozzarella': (None, D('125'), 'pièce'),
    'ail': (D('1'), None, 'gousse'),
    # achetés au poids
    'sucre': (D('1'), None, 'g'),
    'sucre de canne': (D('1'), None, 'g'),
    'sucre roux': (D('1'), None, 'g'),
    'cassonade': (D('1'), None, 'g'),
    'sucre glace': (D('0.53'), None, 'g'),
    'farine': (D('0.67'), None, 'g'),
    'maïzena': (D('0.67'), None, 'g'),
    'beurre': (D('1'), D('250'), 'g'),
    'levure chimique': (D('0.8'), None, 'g'),
    'sel': (D('1.2'), None, 'g'),
    'paprika': (D('0.5'), None, 'g'),
    'poivre noir': (D('0.5'), None, 'g'),
    'poivre blanc': (D('0.5'), None, 'g'),
    'concentré de tomate': (D('1.13'), D('70'), 'g'),
    'tomate pelée en dés': (None, D('400'), 'g'),
    'purée de tomate': (None, D('500'), 'g'),
    'pois chiche': (None, D('265'), 'g'),
    'gingembre': (D('0.4'), D('50'), 'g'),
    'riz basmati': (D('0.8'), None, 'g'),
    'petit pois': (D('0.67'), None, 'g'),
    'raisin sec': (D('0.67'), None, 'g'),
    'câpre': (D('0.67'), None, 'g'),
    'amande': (D('0.6'), None, 'g'),
    'pistache': (D('0.6'), None, 'g'),
    'cacahuète': (D('0.6'), None, 'g'),
    'noix de cajou': (None, None, 'g'),
    'chapelure panko': (D('0.33'), None, 'g'),
    'poulet': (None, D('1500'), 'g'),
    'chorizo': (None, D('225'), 'g'),
    'scampi': (None, D('15'), 'g'),
    "filet d'anchois": (None, D('4'), 'g'),
    'shiitake': (None, D('15'), 'g'),
    'pleurote': (None, D('20'), 'g'),
    # liquides, achetés au volume
    'crème fleurette': (D('1'), None, 'ml'),
    'lait de coco': (D('1'), None, 'ml'),
    'mirin': (D('1'), None, 'ml'),
    'sauce soja noir': (D('1'), None, 'ml'),
    'sauce soja': (D('1'), None, 'ml'),
}

# produit, mesure, quantité, unité de référence (None = pièces)
MESURES = [
    ('ail', 'gousse', D('5'), 'g'),
    ('gingembre', 'cm', D('5'), 'g'),
    ('gingembre', 'tranche', D('3'), 'g'),
    ('poireau', 'botte', D('3'), None),
    ('noix de cajou', 'poignée', D('30'), 'g'),
]


def _unites(Unite):
    # pincée : volume approximatif, convertible en grammes grâce à la densité du produit
    Unite.objects.filter(code='pincée', dimension='vague').update(dimension='volume', facteur=D('0.5'))
    # cm (de gingembre, de cannelle) : la valeur dépend du produit
    Unite.objects.filter(code='cm').exclude(dimension='vague').update(dimension='vague', facteur=None)
    Unite.objects.get_or_create(code='pièce', defaults={
        'pluriel': 'pièces', 'description': 'Pièce (unité d\'achat)', 'dimension': 'piece', 'facteur': D('1'),
    })


def _sortir_preparations(Produit, Ingredient, Article):
    nb = 0
    for nom_prepare, nom_base, preparation in PREPARATIONS:
        prepare = Produit.objects.filter(nom__iexact=nom_prepare).first()
        base = Produit.objects.filter(nom__iexact=nom_base).first()
        if not prepare or not base or prepare.pk == base.pk:
            continue
        nb += Ingredient.objects.filter(produit=prepare, preparation='').update(produit=base, preparation=preparation)
        nb += Ingredient.objects.filter(produit=prepare).update(produit=base)
        Produit.objects.filter(produitDeBase=prepare).update(produitDeBase=base)
        Article.objects.filter(produit=prepare).update(produit=base)
        prepare.delete()
    return nb


def _volume_vers_jus(Produit, Ingredient):
    nb = 0
    for nom_produit, nom_jus in VOLUME_EST_UN_JUS:
        produit = Produit.objects.filter(nom__iexact=nom_produit).first()
        jus = Produit.objects.filter(nom__iexact=nom_jus).first()
        if produit and jus:
            nb += Ingredient.objects.filter(produit=produit, unite__dimension='volume').update(produit=jus)
    return nb


def _proprietes(Produit, Unite, ProduitMesure):
    unites = {u.code: u for u in Unite.objects.all()}
    nb = 0
    for nom, (densite, poids_piece, code_achat) in PROPRIETES.items():
        produit = Produit.objects.filter(nom__iexact=nom).first()
        if produit is None:
            continue
        champs = []
        if produit.densite is None and densite is not None:
            produit.densite = densite
            champs.append('densite')
        if produit.poidsPiece is None and poids_piece is not None:
            produit.poidsPiece = poids_piece
            champs.append('poidsPiece')
        if produit.uniteAchat_id is None and code_achat in unites:
            produit.uniteAchat = unites[code_achat]
            champs.append('uniteAchat')
        if champs:
            produit.save(update_fields=champs)
            nb += 1

    for nom, code, quantite, code_reference in MESURES:
        produit = Produit.objects.filter(nom__iexact=nom).first()
        unite = unites.get(code)
        if produit and unite and (code_reference is None or code_reference in unites):
            ProduitMesure.objects.get_or_create(produit=produit, unite=unite, defaults={
                'quantite': quantite, 'uniteReference': unites.get(code_reference) if code_reference else None,
            })
    return nb


def convertir(apps, schema_editor):
    Unite = apps.get_model('recette', 'Unite')
    Produit = apps.get_model('recette', 'Produit')
    ProduitMesure = apps.get_model('recette', 'ProduitMesure')
    Ingredient = apps.get_model('recette', 'Ingredient')
    Article = apps.get_model('listeCourse', 'ListeCourseArticle')

    _unites(Unite)
    nb_preparations = _sortir_preparations(Produit, Ingredient, Article)
    nb_jus = _volume_vers_jus(Produit, Ingredient)
    nb_produits = _proprietes(Produit, Unite, ProduitMesure)
    print(f"\n  {nb_preparations} ingrédient(s) préparé(s) rattaché(s) à leur produit, {nb_jus} volume(s) de citron -> jus, "
          f"{nb_produits} produit(s) avec conversions, {ProduitMesure.objects.count()} mesure(s)")


class Migration(migrations.Migration):

    dependencies = [
        ('recette', '0038_mesures_densite_preparation'),
        ('listeCourse', '0001_initial'),
    ]

    operations = [
        # pas de retour arrière des données : faire une sauvegarde de la base avant d'appliquer en production
        migrations.RunPython(convertir, migrations.RunPython.noop),
    ]
