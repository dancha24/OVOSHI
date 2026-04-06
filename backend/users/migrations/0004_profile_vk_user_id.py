from django.db import migrations, models


def backfill_vk_user_id(apps, schema_editor):
    SocialAccount = apps.get_model('socialaccount', 'SocialAccount')
    Profile = apps.get_model('users', 'Profile')
    for sa in SocialAccount.objects.filter(provider__in=('vk', 'vk_oauth2')):
        try:
            uid = int(str(sa.uid).strip())
        except (ValueError, TypeError):
            continue
        if uid < 1:
            continue
        profile, _ = Profile.objects.get_or_create(user_id=sa.user_id)
        if profile.vk_user_id is None:
            profile.vk_user_id = uid
            profile.save(update_fields=['vk_user_id'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_remove_profile_telegram_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='vk_user_id',
            field=models.BigIntegerField(
                blank=True,
                null=True,
                unique=True,
                verbose_name='ID ВКонтакте',
                help_text='Совпадает с vk.com/id…; подставляется при входе через ВК',
            ),
        ),
        migrations.RunPython(backfill_vk_user_id, noop_reverse),
    ]
