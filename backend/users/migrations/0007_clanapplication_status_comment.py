from django.db import migrations, models


def fill_pending_comment(apps, schema_editor):
    ClanApplication = apps.get_model('users', 'ClanApplication')
    ClanApplication.objects.filter(status='pending', status_comment='').update(
        status_comment='На рассмотрении'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_profile_age_city_clanapplication'),
    ]

    operations = [
        migrations.AddField(
            model_name='clanapplication',
            name='status_comment',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Показывается пользователю в боте. Для новой заявки задаётся «На рассмотрении»; лидер может изменить при смене статуса.',
                verbose_name='Комментарий',
            ),
        ),
        migrations.RunPython(fill_pending_comment, migrations.RunPython.noop),
    ]
