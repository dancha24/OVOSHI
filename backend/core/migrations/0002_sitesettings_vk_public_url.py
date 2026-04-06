# Generated manually for clan VK public link

from django.db import migrations, models


def seed_vk_public_url(apps, schema_editor):
    SiteSettings = apps.get_model('core', 'SiteSettings')
    obj, _ = SiteSettings.objects.get_or_create(pk=1)
    if not obj.vk_public_url:
        obj.vk_public_url = 'https://vk.com/ovoshi_pubg'
        obj.save(update_fields=['vk_public_url'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='vk_public_url',
            field=models.URLField(
                blank=True,
                max_length=500,
                verbose_name='Ссылка на паблик клана ВКонтакте',
            ),
        ),
        migrations.RunPython(seed_vk_public_url, noop),
    ]
