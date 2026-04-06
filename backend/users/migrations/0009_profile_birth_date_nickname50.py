# Дата рождения вместо возраста; никнейм до 50 символов.

import datetime

from django.db import migrations, models
from django.utils import timezone


def forwards(apps, schema_editor):
    Profile = apps.get_model('users', 'Profile')
    ClanApplication = apps.get_model('users', 'ClanApplication')
    today = timezone.now().date()
    for p in Profile.objects.all():
        if p.nickname and len(p.nickname) > 50:
            p.nickname = p.nickname[:50]
            p.save(update_fields=['nickname'])
        if getattr(p, 'age', None) is not None:
            try:
                a = int(p.age)
            except (TypeError, ValueError):
                continue
            if 5 <= a <= 120:
                y = today.year - a
                p.birth_date = datetime.date(y, 6, 15)
                p.save(update_fields=['birth_date'])
    for app in ClanApplication.objects.all():
        if getattr(app, 'age', None) is not None:
            try:
                a = int(app.age)
            except (TypeError, ValueError):
                continue
            if 5 <= a <= 120:
                y = today.year - a
                app.birth_date = datetime.date(y, 6, 15)
                app.save(update_fields=['birth_date'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_clanpointsentry_deputy_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='birth_date',
            field=models.DateField(blank=True, null=True, verbose_name='Дата рождения'),
        ),
        migrations.AddField(
            model_name='clanapplication',
            name='birth_date',
            field=models.DateField(blank=True, null=True, verbose_name='Дата рождения'),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='profile',
            name='age',
        ),
        migrations.RemoveField(
            model_name='clanapplication',
            name='age',
        ),
        migrations.AlterField(
            model_name='profile',
            name='nickname',
            field=models.CharField(blank=True, max_length=50, verbose_name='Никнейм'),
        ),
    ]
