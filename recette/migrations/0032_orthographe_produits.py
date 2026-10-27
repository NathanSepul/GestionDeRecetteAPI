"""
Orthographe des produits : noms, pluriels et déterminants ("de" / "d'").

Comme les 0030 et 0031, prévu pour la production : tout se fait par nom (jamais par id),
un produit absent est ignoré ; si le nom corrigé existe déjà, les deux produits sont fusionnés.
Le déterminant est recalculé pour tous les produits à partir du nom (élision devant voyelle et h muet).
"""
from django.db import migrations


# nom actuel -> (nom corrigé, pluriel corrigé)
CORRECTIONS = {
    'ail haché': ('ail haché', 'ail haché'),
    'Amaretto': ('amaretto', 'amaretto'),
    'asperge verte': ('asperge verte', 'asperges vertes'),
    'baguette précuites au levain': ('baguette précuite au levain', 'baguettes précuites au levain'),
    'bébé pak-choy': ('bébé pak-choï', 'bébés pak-choï'),
    'beurre doux': ('beurre doux', 'beurre doux'),
    'beurre doux fondu': ('beurre doux fondu', 'beurre doux fondu'),
    'blanc de poulet': ('blanc de poulet', 'blancs de poulet'),
    'bonbon à la violette': ('bonbon à la violette', 'bonbons à la violette'),
    'bouillon de boeuf': ('bouillon de bœuf', 'bouillon de bœuf'),
    'cacahuète au miel piquante': ('cacahuète au miel piquante', 'cacahuètes au miel piquantes'),
    'câpre': ('câpre', 'câpres'),
    'carbonade de boeuf': ('carbonade de bœuf', 'carbonades de bœuf'),
    'carotte jaune': ('carotte jaune', 'carottes jaunes'),
    'céleri blanc': ('céleri blanc', 'céleris blancs'),
    'champignon noir déshydraté': ('champignon noir déshydraté', 'champignons noirs déshydratés'),
    'citron vert': ('citron vert', 'citrons verts'),
    'courgette ronde': ('courgette ronde', 'courgettes rondes'),
    'crevette tigrée jumbo': ('crevette tigrée jumbo', 'crevettes tigrées jumbo'),
    'dos de saumon atlantique (surgelés)': ('dos de saumon atlantique surgelé', 'dos de saumon atlantique surgelés'),
    'échalote coupées finement': ('échalote coupée finement', 'échalotes coupées finement'),
    'épaule d\'agneau': ('épaule d\'agneau', 'épaules d\'agneau'),
    'fécule de pdt': ('fécule de pomme de terre', 'fécule de pomme de terre'),
    'feuille de Wonton': ('feuille de wonton', 'feuilles de wonton'),
    'germe de soja': ('germe de soja', 'germes de soja'),
    'graine de sésame': ('graine de sésame', 'graines de sésame'),
    'haricot rouge': ('haricot rouge', 'haricots rouges'),
    'haricot vert': ('haricot vert', 'haricots verts'),
    'herbes de provence': ('herbes de Provence', 'herbes de Provence'),
    'jaret de boeuf': ('jarret de bœuf', 'jarrets de bœuf'),
    'jaune d\'œuf': ('jaune d\'œuf', 'jaunes d\'œuf'),
    'jus de citrons': ('jus de citron', 'jus de citron'),
    'jus de pommes': ('jus de pomme', 'jus de pomme'),
    'Ketjap Manis': ('ketjap manis', 'ketjap manis'),
    'lardon fumé': ('lardon fumé', 'lardons fumés'),
    'Macaroni': ('macaroni', 'macaroni'),
    'noix de saint-jacques': ('noix de Saint-Jacques', 'noix de Saint-Jacques'),
    'nouille instantanée': ('nouille instantanée', 'nouilles instantanées'),
    'nouille Ramen prêt à l’emplois': ('nouille ramen prête à l\'emploi', 'nouilles ramen prêtes à l\'emploi'),
    'nouille udon': ('nouille udon', 'nouilles udon'),
    'nouilles de riz': ('nouille de riz', 'nouilles de riz'),
    'oignon émincé': ('oignon émincé', 'oignons émincés'),
    'oignon haché': ('oignon haché', 'oignons hachés'),
    'oignon rouge': ('oignon rouge', 'oignons rouges'),
    'pak-choï': ('pak-choï', 'pak-choïs'),
    'piment d\'espelette': ('piment d\'Espelette', 'piment d\'Espelette'),
    'pignons de pin': ('pignon de pin', 'pignons de pin'),
    'pistache pelées non salée': ('pistache pelée non salée', 'pistaches pelées non salées'),
    'pois chiche': ('pois chiche', 'pois chiches'),
    'poivre de cayenne': ('poivre de Cayenne', 'poivre de Cayenne'),
    'poivre de sichuan': ('poivre de Sichuan', 'poivre de Sichuan'),
    'pomme de terre grenaille': ('pomme de terre grenaille', 'pommes de terre grenaille'),
    'pomme de terre précuit': ('pomme de terre précuite', 'pommes de terre précuites'),
    'raisin sec trempé': ('raisin sec trempé', 'raisins secs trempés'),
    'raisins sec': ('raisin sec', 'raisins secs'),
    'sauce aigre douce pimentée': ('sauce aigre-douce pimentée', 'sauce aigre-douce pimentée'),
    'sauce huître': ('sauce d\'huître', 'sauce d\'huître'),
    'sauce worcestershire': ('sauce Worcestershire', 'sauce Worcestershire'),
    'shitake': ('shiitake', 'shiitakes'),
    'tomates cerises de différentes couleurs': ('tomate cerise de différentes couleurs', 'tomates cerises de différentes couleurs'),
    'tomates séchées': ('tomate séchée', 'tomates séchées'),
    'vermicelle de riz': ('vermicelle de riz', 'vermicelles de riz'),
    'vermicelles transparent': ('vermicelle transparent', 'vermicelles transparents'),
    'yaourt nature': ('yaourt nature', 'yaourts nature'),
}

# "quelques feuilles de basilic" : la quantité est dans le nom -> produit "basilic" + unité "feuille"
UNITES_DANS_LE_NOM = [
    ('quelques feuilles de basilic', 'basilic', 'feuille'),
]

# h aspiré : pas d'élision ("de haricots", "de harissa")
H_ASPIRE = ('haché', 'haricot', 'harissa', 'haut', 'houmous')


def _determinant(nom):
    debut = nom.lower()
    if debut.startswith('h'):
        return 'de' if debut.startswith(H_ASPIRE) else "d'"
    return "d'" if debut[:1] in 'aeiouéèêàâîôûœ' else 'de'


def _apostrophes(texte):
    return texte.replace('’', "'")


def _fusionner(Produit, Ingredient, ancien, nouveau, unite=None):
    """Repointe ingrédients et produitDeBase de l'ancien produit vers le nouveau, puis supprime l'ancien s'il n'est plus utilisé."""
    ingredients = Ingredient.objects.filter(produit=ancien)
    if unite is None:
        ingredients.update(produit=nouveau)
    else:
        ingredients.filter(unite__isnull=True).update(produit=nouveau, unite=unite)

    Produit.objects.filter(produitDeBase=ancien).exclude(pk=nouveau.pk).update(produitDeBase=nouveau)
    if nouveau.produitDeBase_id == ancien.pk:
        nouveau.produitDeBase = None
        nouveau.save(update_fields=['produitDeBase'])

    if not Ingredient.objects.filter(produit=ancien).exists():
        ancien.delete()


def _renommer(Produit, Ingredient, produit, nom, pluriel):
    """Renomme le produit ; si un autre produit porte déjà ce nom, fusionne dans celui-ci."""
    existant = Produit.objects.filter(nom__iexact=nom).exclude(pk=produit.pk).first()
    if existant:
        _fusionner(Produit, Ingredient, produit, existant)
        return 1
    produit.nom, produit.nomPluriel = nom, pluriel
    produit.save(update_fields=['nom', 'nomPluriel'])
    return 0


def corriger_orthographe(apps, schema_editor):
    Unite = apps.get_model('recette', 'Unite')
    Produit = apps.get_model('recette', 'Produit')
    Ingredient = apps.get_model('recette', 'Ingredient')
    nb_fusions = 0

    for nom_ancien, nom_cible, code_unite in UNITES_DANS_LE_NOM:
        ancien = Produit.objects.filter(nom__iexact=nom_ancien).first()
        cible = Produit.objects.filter(nom__iexact=nom_cible).first()
        unite = Unite.objects.filter(code=code_unite).first()
        if ancien and cible and unite:
            _fusionner(Produit, Ingredient, ancien, cible, unite)
            nb_fusions += 1

    for nom_actuel, (nom, pluriel) in CORRECTIONS.items():
        # nom exact (sensible à la casse) : "Macaroni" -> "macaroni" ne doit pas toucher "maccheroni"
        produit = Produit.objects.filter(nom=nom_actuel).first()
        if produit:
            nb_fusions += _renommer(Produit, Ingredient, produit, nom, pluriel)

    # tous les produits : apostrophes droites, pluriel par défaut, déterminant recalculé
    nb_modifies = 0
    for produit in Produit.objects.all():
        nom, pluriel = _apostrophes(produit.nom), _apostrophes(produit.nomPluriel or produit.nom)
        determinant = _determinant(nom)
        if (nom, pluriel, determinant) == (produit.nom, produit.nomPluriel, produit.determinant):
            continue
        if nom != produit.nom and Produit.objects.filter(nom__iexact=nom).exclude(pk=produit.pk).exists():
            nb_fusions += _renommer(Produit, Ingredient, produit, nom, pluriel)
            continue
        produit.nom, produit.nomPluriel, produit.determinant = nom, pluriel, determinant
        produit.save(update_fields=['nom', 'nomPluriel', 'determinant'])
        nb_modifies += 1

    print(f"\n  {nb_modifies} produit(s) corrigé(s), {nb_fusions} fusion(s)")


class Migration(migrations.Migration):

    dependencies = [
        ('recette', '0031_nettoyage_produits'),
    ]

    operations = [
        # pas de retour arrière des données : faire une sauvegarde de la base avant d'appliquer en production
        migrations.RunPython(corriger_orthographe, migrations.RunPython.noop),
    ]
