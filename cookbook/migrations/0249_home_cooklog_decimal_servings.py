# home: upstream 2.7.2 made CookLog.servings a DecimalField (15e6d3f8) without a migration
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('cookbook', '0248_home_merge_2_7'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cooklog',
            name='servings',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True),
        ),
    ]
