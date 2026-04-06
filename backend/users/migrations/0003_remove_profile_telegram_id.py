from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_profile_telegram_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='telegram_id',
        ),
    ]
