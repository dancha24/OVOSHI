from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_sitesettings_recruiter_url'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sitesettings',
            name='telegram_channel_url',
        ),
    ]
