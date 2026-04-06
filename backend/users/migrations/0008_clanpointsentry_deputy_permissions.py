import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_clanapplication_status_comment'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClanPointsEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.IntegerField(verbose_name='Сумма ОК')),
                ('comment', models.CharField(blank=True, default='', max_length=500, verbose_name='Комментарий')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Когда')),
                (
                    'created_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='clan_points_entries_created',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Кем начислено / списано',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='clan_points_entries',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Игрок',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Запись журнала ОК',
                'verbose_name_plural': 'Журнал ОК',
                'ordering': ['-created_at'],
            },
        ),
    ]
