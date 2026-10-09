# home fork: pantry stock layer — count/edit/undo bookings, who booked, last counted, product info, stock counts
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cookbook', '0244_home_food_barcodes'),
    ]

    operations = [
        migrations.AddField(
            model_name='food',
            name='product_info',
            field=models.JSONField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='inventoryentry',
            name='counted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='inventorylog',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='inventorylog',
            name='booking_type',
            field=models.CharField(choices=[('add', 'Add'), ('remove', 'Remove'), ('move', 'Move'), ('count', 'Count'), ('edit', 'Edit'), ('undo', 'Undo')], default='add', max_length=10),
        ),
        migrations.CreateModel(
            name='StockCount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sub_location', models.CharField(blank=True, default='', max_length=64)),
                ('status', models.CharField(choices=[('open', 'Open'), ('applied', 'Applied'), ('discarded', 'Discarded')], default='open', max_length=16)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('inventory_location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cookbook.inventorylocation')),
                ('space', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cookbook.space')),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.CreateModel(
            name='StockCountLine',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recorded', models.DecimalField(decimal_places=16, default=0, max_digits=32)),
                ('counted', models.DecimalField(decimal_places=16, default=0, max_digits=32)),
                ('applied', models.BooleanField(default=False)),
                ('result', models.CharField(blank=True, default='', max_length=256)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('count', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='cookbook.stockcount')),
                ('food', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cookbook.food')),
                ('space', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cookbook.space')),
                ('unit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='cookbook.unit')),
            ],
            options={'ordering': ('id',)},
        ),
    ]
