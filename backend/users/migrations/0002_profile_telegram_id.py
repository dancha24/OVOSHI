from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='telegram_id',
            field=models.BigIntegerField(blank=True, null=True, unique=True, verbose_name='Telegram ID'),
        ),
    ]
