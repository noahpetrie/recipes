# home fork: printed cookbooks vs. collections, with an author and a cover
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cookbook', '0242_space_household_setup_completed'),
    ]

    operations = [
        migrations.AddField(
            model_name='recipebook',
            name='kind',
            field=models.CharField(choices=[('collection', 'Collection'), ('cookbook', 'Cookbook')], default='collection', max_length=16),
        ),
        migrations.AddField(
            model_name='recipebook',
            name='author',
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AddField(
            model_name='recipebook',
            name='cover',
            field=models.ImageField(blank=True, null=True, upload_to='books/'),
        ),
    ]
