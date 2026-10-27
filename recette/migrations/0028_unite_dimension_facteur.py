from decimal import Decimal
from django.db import migrations, models
from django.db.models import Q


# code -> (dimension, facteur vers l'unité de base : g, ml, pièce, cm)
# Les codes absents de cette table restent 'vague' : ils s'additionnent seulement entre eux, comme avant.
UNITES = {
    'l': ('volume', Decimal('1000')),
    'dl': ('volume', Decimal('100')),
    'cl': ('volume', Decimal('10')),
    'ml': ('volume', Decimal('1')),
    'cs': ('volume', Decimal('15')),
    'cc': ('volume', Decimal('5')),
    'kg': ('masse', Decimal('1000')),
    'g': ('masse', Decimal('1')),
    'u': ('piece', Decimal('1')),
    'cm': ('longueur', Decimal('1')),
}


def remplir_dimensions(apps, schema_editor):
    Unite = apps.get_model('recette', 'Unite')
    for unite in Unite.objects.all():
        if unite.code in UNITES:
            unite.dimension, unite.facteur = UNITES[unite.code]
            unite.save(update_fields=['dimension', 'facteur'])


def vider_dimensions(apps, schema_editor):
    Unite = apps.get_model('recette', 'Unite')
    Unite.objects.update(dimension='vague', facteur=None)


class Migration(migrations.Migration):

    dependencies = [
        ('recette', '0027_alter_recette_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='unite',
            name='dimension',
            field=models.CharField(
                choices=[('masse', 'Masse (base : g)'), ('volume', 'Volume (base : ml)'), ('piece', 'Pièce'),
                         ('longueur', 'Longueur (base : cm)'), ('vague', 'Non convertible (pincée...)')],
                default='vague', max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='unite',
            name='facteur',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=12, null=True),
        ),
        migrations.RunPython(remplir_dimensions, vider_dimensions),
        migrations.AddConstraint(
            model_name='unite',
            constraint=models.CheckConstraint(
                condition=Q(dimension='vague') | Q(facteur__isnull=False),
                name='unite_facteur_obligatoire_si_convertible',
            ),
        ),
    ]
