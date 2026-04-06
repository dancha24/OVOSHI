# Ссылка на наборщика для бота ВК

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_seed_shop_lots'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='recruiter_url',
            field=models.URLField(
                blank=True,
                help_text='Используется в боте ВК в тексте «Вступить» (напиши наборщику). Если пусто — из VK_BOT_RECRUITER_URL в .env.',
                max_length=500,
                verbose_name='Ссылка на наборщика',
            ),
        ),
    ]
