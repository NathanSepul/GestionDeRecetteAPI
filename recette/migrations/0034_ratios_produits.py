"""
Ratios entre un produit dérivé et son produit de base, pour la liste de courses :
"1,5 dl de jus de citron" -> "4 citrons".

Prévu pour la production : tout se fait par nom (jamais par id), un produit ou une unité absents sont ignorés,
un ratio déjà renseigné (à la main dans l'admin) n'est pas écrasé.
"""
from decimal import Decimal
from django.db import migrations


# produit dérivé : quantité de base, unité de base (None = sans unité), quantité dérivée, unité dérivée
RATIOS = [
    ('jus de citron', Decimal('1'), None, Decimal('40'), 'ml'),
    ('jus de citron vert', Decimal('1'), None, Decimal('30'), 'ml'),
    ('ail haché', Decimal('1'), 'gousse', Decimal('1'), 'cc'),
    ('oignon émincé', Decimal('1'), None, Decimal('150'), 'g'),
    ('oignon haché', Decimal('1'), None, Decimal('15'), 'cl'),
    ('amande effilée', Decimal('8'), 'g', Decimal('1'), 'cs'),
    ('pistache pelée non salée', Decimal('10'), 'g', Decimal('1'), 'cs'),
    ('jus de gingembre', Decimal('3'), 'cm', Decimal('5'), 'ml'),
]


def renseigner_ratios(apps, schema_editor):
    Produit = apps.get_model('recette', 'Produit')
    Unite = apps.get_model('recette', 'Unite')
    nb = 0

    for nom, quantite_base, code_base, quantite, code in RATIOS:
        produit = Produit.objects.filter(nom__iexact=nom, produitDeBase__isnull=False, ratioQuantite__isnull=True).first()
        unite_base = Unite.objects.filter(code=code_base).first() if code_base else None
        unite = Unite.objects.filter(code=code).first() if code else None
        if produit is None or (code_base and unite_base is None) or (code and unite is None):
            continue
        produit.ratioQuantiteBase, produit.ratioUniteBase = quantite_base, unite_base
        produit.ratioQuantite, produit.ratioUnite = quantite, unite
        produit.save(update_fields=['ratioQuantiteBase', 'ratioUniteBase', 'ratioQuantite', 'ratioUnite'])
        nb += 1

    print(f"\n  {nb} ratio(s) renseigné(s)")


class Migration(migrations.Migration):

    dependencies = [
        ('recette', '0033_produit_ratio'),
    ]

    operations = [
        migrations.RunPython(renseigner_ratios, migrations.RunPython.noop),
    ]
