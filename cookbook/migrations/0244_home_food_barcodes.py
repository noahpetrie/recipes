# home fork: product barcodes on foods for pantry scanning, and the Homebox link for synced cookbooks
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cookbook', '0243_home_recipebook_kind_author_cover'),
    ]

    operations = [
        migrations.AddField(
            model_name='food',
            name='barcodes',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='recipebook',
            name='homebox_id',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
