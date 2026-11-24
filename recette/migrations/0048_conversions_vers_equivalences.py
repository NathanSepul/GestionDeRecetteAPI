"""
Refonte des produits, partie données :
1. densité, poids d'une pièce, mesures propres au produit et ratios -> équivalences (rien n'est supprimé ici) ;
2. produits qui ne sont qu'une façon d'écrire leur produit de base -> synonymes ; les ingrédients des recettes
   (et articles de listes de courses) passent sur le produit de base, la précision va dans la préparation ;
3. unités : boîte, pot, verre, morceau ajoutées ; cm passe en longueur.
Réversible pour les équivalences et unités ; la fusion des variantes, elle, ne se défait pas (sauvegarde avant migration).
"""
import re
import unicodedata

from django.db import migrations

# variante -> (produit de base, précision gardée sur l'ingrédient)
VARIANTES = {
    'beurre doux': ('beurre', 'doux'),
    'petit poireau': ('poireau', 'petit'),
    'tomate cerise de différentes couleurs': ('tomate cerise', 'de différentes couleurs'),
    'huile neutre pour friture': ('huile neutre', 'pour friture'),
    'harissa en tube': ('harissa', 'en tube'),
    'plant de ciboulette': ('ciboulette', 'en plant'),
    'plant de persil plat': ('persil plat', 'en plant'),
}

UNITES = [('boîte', 'boîtes', 'boîte (conserve)'), ('pot', 'pots', 'pot'), ('verre', 'verres', 'verre'), ('morceau', 'morceaux', 'morceau')]


def normaliser_nom(texte):
    texte = (texte or '').lower().replace('œ', 'oe').replace('æ', 'ae').replace('’', "'")
    texte = ''.join(c for c in unicodedata.normalize('NFD', texte) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', texte).strip()


def vers_equivalences(apps, schema_editor):
    Produit = apps.get_model('recette', 'Produit')
    ProduitMesure = apps.get_model('recette', 'ProduitMesure')
    Equivalence = apps.get_model('recette', 'Equivalence')
    Unite = apps.get_model('recette', 'Unite')
    g = Unite.objects.filter(code='g').first()
    ml = Unite.objects.filter(code='ml').first()

    for produit in Produit.objects.all():
        if produit.densite and ml and g:
            Equivalence.objects.create(produit=produit, quantite=1, unite=ml, quantiteCible=produit.densite, uniteCible=g)
        if produit.poidsPiece and g:
            Equivalence.objects.create(produit=produit, quantite=1, unite=None, quantiteCible=produit.poidsPiece, uniteCible=g)
        if produit.produitDeBase_id and produit.ratioQuantite and produit.ratioQuantiteBase:
            Equivalence.objects.create(produit=produit, quantite=produit.ratioQuantite, unite_id=produit.ratioUnite_id,
                                       produitCible_id=produit.produitDeBase_id, quantiteCible=produit.ratioQuantiteBase,
                                       uniteCible_id=produit.ratioUniteBase_id)
    for mesure in ProduitMesure.objects.all():
        Equivalence.objects.create(produit_id=mesure.produit_id, quantite=1, unite_id=mesure.unite_id,
                                   quantiteCible=mesure.quantite, uniteCible_id=mesure.uniteReference_id)


def fusionner_variantes(apps, schema_editor):
    Produit = apps.get_model('recette', 'Produit')
    Synonyme = apps.get_model('recette', 'Synonyme')
    Ingredient = apps.get_model('recette', 'Ingredient')
    ListeCourseArticle = apps.get_model('listeCourse', 'ListeCourseArticle')

    for nom_variante, (nom_base, precision) in VARIANTES.items():
        variante = Produit.objects.filter(nom=nom_variante).first()
        base = Produit.objects.filter(nom=nom_base).first()
        if not variante or not base:
            continue
        for ingredient in Ingredient.objects.filter(produit=variante):
            ingredient.produit = base
            ingredient.preparation = ', '.join(p for p in (precision, ingredient.preparation) if p)[:50]
            ingredient.save(update_fields=['produit', 'preparation'])
        ListeCourseArticle.objects.filter(produit=variante).update(produit=base, precision=nom_variante)
        Produit.objects.filter(produitDeBase=variante).update(produitDeBase=base)
        for texte in {variante.nom, variante.nomPluriel}:
            if texte and not Synonyme.objects.filter(cle=normaliser_nom(texte)).exists():
                Synonyme.objects.create(texte=texte, cle=normaliser_nom(texte), produit=base)
        variante.delete()


def unites(apps, schema_editor):
    Unite = apps.get_model('recette', 'Unite')
    for code, pluriel, description in UNITES:
        Unite.objects.get_or_create(code=code, defaults={'pluriel': pluriel, 'description': description, 'dimension': 'vague'})
    Unite.objects.filter(code='cm', dimension='vague').update(dimension='longueur', facteur=1)


def annuler_equivalences(apps, schema_editor):
    apps.get_model('recette', 'Equivalence').objects.all().delete()


def annuler_unites(apps, schema_editor):
    Unite = apps.get_model('recette', 'Unite')
    Unite.objects.filter(code='cm').update(dimension='vague', facteur=None)


class Migration(migrations.Migration):

    dependencies = [
        ('recette', '0047_synonymes_equivalences'),
        ('listeCourse', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(vers_equivalences, annuler_equivalences),
        migrations.RunPython(fusionner_variantes, migrations.RunPython.noop),
        migrations.RunPython(unites, annuler_unites),
    ]
