# home fork: kitchen equipment and what each recipe needs (cookbook/helper/home_equipment.py)
import django.db.models.deletion
from django.db import migrations, models

import cookbook.models


class Migration(migrations.Migration):

    dependencies = [
        ('cookbook', '0246_home_recipe_origin'),
    ]

    operations = [
        migrations.CreateModel(
            name='Equipment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('owned', models.BooleanField(default=False)),
                ('hidden', models.BooleanField(default=False)),
                ('homebox_id', models.CharField(blank=True, max_length=64, null=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='equipment/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('general', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='specific', to='cookbook.equipment')),
                ('space', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cookbook.space')),
            ],
            options={'ordering': ('name',)},
            bases=(models.Model, cookbook.models.PermissionModelMixin),
        ),
        migrations.CreateModel(
            name='RecipeEquipment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('optional', models.BooleanField(default=False)),
                ('note', models.CharField(blank=True, default='', max_length=64)),
                ('order', models.IntegerField(default=0)),
                ('equipment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipe_lines', to='cookbook.equipment')),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equipment_lines', to='cookbook.recipe')),
                ('space', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cookbook.space')),
            ],
            options={'ordering': ('order', 'id')},
            bases=(models.Model, cookbook.models.PermissionModelMixin),
        ),
        migrations.AddField(
            model_name='recipe',
            name='equipment_checked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name='recipeequipment',
            constraint=models.UniqueConstraint(fields=('recipe', 'equipment'), name='home_recipe_equipment_unique'),
        ),
    ]
