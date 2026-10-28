from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recette', '0036_rayons_produits'),
    ]

    operations = [
        migrations.AddField(
            model_name='recette',
            name='source',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]
