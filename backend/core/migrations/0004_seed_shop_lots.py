# Data migration: каталог магазина (ОК)

from django.db import migrations


def seed_lots(apps, schema_editor):
    ShopLot = apps.get_model('core', 'ShopLot')
    rows = (
        ('60 UC', 120, 0),
        ('180 UC', 300, 1),
        ('Напальчники', 300, 2),
        ('Стать Элитой', 500, 3),
    )
    for title, price_points, sort_order in rows:
        ShopLot.objects.update_or_create(
            title=title,
            defaults={
                'price_points': price_points,
                'sort_order': sort_order,
                'is_active': True,
            },
        )


def unseed_lots(apps, schema_editor):
    ShopLot = apps.get_model('core', 'ShopLot')
    titles = ('60 UC', '180 UC', 'Напальчники', 'Стать Элитой')
    ShopLot.objects.filter(title__in=titles).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_shoplot'),
    ]

    operations = [
        migrations.RunPython(seed_lots, unseed_lots),
    ]
