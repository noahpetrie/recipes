# home: joins upstream 2.7's 0243 with the fork's 0243-0247 chain
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('cookbook', '0243_auto_20261018_1149'),
        ('cookbook', '0247_home_equipment'),
    ]

    operations = []
