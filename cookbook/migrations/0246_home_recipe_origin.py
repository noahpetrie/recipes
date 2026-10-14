# home fork: where a recipe comes from (country and region), for the food map
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cookbook', '0245_home_pantry_stock'),
    ]

    operations = [
        migrations.AddField(
            model_name='recipe',
            name='origin_country',
            field=models.CharField(blank=True, default='', max_length=2),
        ),
        migrations.AddField(
            model_name='recipe',
            name='origin_region',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
    ]
