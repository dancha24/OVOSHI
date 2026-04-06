# Generated manually for ShopLot

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_sitesettings_vk_public_url'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShopLot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Название')),
                ('image', models.ImageField(blank=True, null=True, upload_to='shop/', verbose_name='Картинка')),
                ('price_points', models.PositiveIntegerField(verbose_name='Цена, ОК')),
                ('sort_order', models.PositiveSmallIntegerField(default=0, verbose_name='Порядок')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Лот магазина',
                'verbose_name_plural': 'Лоты магазина',
                'ordering': ('sort_order', 'id'),
            },
        ),
    ]
