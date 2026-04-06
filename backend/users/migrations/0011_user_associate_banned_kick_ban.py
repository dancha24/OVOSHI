from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_clanapplication_resolved_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('guest', 'Гость'),
                    ('player', 'Игрок'),
                    ('elite', 'Элита'),
                    ('deputy', 'Заместитель'),
                    ('leader', 'Лидер'),
                    ('associate', 'Соучастник'),
                    ('banned', 'Забанен'),
                ],
                default='guest',
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='ban_reason',
            field=models.TextField(blank=True, default='', verbose_name='Причина бана'),
        ),
        migrations.AddField(
            model_name='user',
            name='banned_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Забанен'),
        ),
        migrations.AddField(
            model_name='user',
            name='banned_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='clan_bans_executed',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Забанил',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='kick_reason',
            field=models.TextField(blank=True, default='', verbose_name='Причина исключения'),
        ),
        migrations.AddField(
            model_name='user',
            name='kicked_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Исключён из клана'),
        ),
        migrations.AddField(
            model_name='user',
            name='kicked_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='clan_kicks_executed',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Исключил',
            ),
        ),
    ]
