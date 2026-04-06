# Дата/время решения по заявке

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_profile_birth_date_nickname50'),
    ]

    operations = [
        migrations.AddField(
            model_name='clanapplication',
            name='resolved_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Заполняется при переводе заявки в «Принята» или «Отклонена».',
                null=True,
                verbose_name='Дата и время решения',
            ),
        ),
        migrations.AlterField(
            model_name='clanapplication',
            name='status_comment',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Показывается пользователю в боте. Для новой заявки задаётся «На рассмотрении»; при принятии/отклонении лидер обязан указать свой комментарий.',
                verbose_name='Комментарий',
            ),
        ),
    ]
