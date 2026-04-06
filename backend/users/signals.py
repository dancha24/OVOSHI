from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, Profile


@receiver(post_save, sender=User)
def create_profile_for_user(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'profile'):
        Profile.objects.get_or_create(user=instance)


def _register_socialaccount_signal():
    try:
        from allauth.socialaccount.models import SocialAccount
    except ImportError:
        return

    @receiver(post_save, sender=SocialAccount)
    def sync_vk_user_id_from_social(sender, instance, **kwargs):
        if instance.provider not in ('vk', 'vk_oauth2'):
            return
        try:
            uid = int(str(instance.uid).strip())
        except (ValueError, TypeError):
            return
        if uid < 1:
            return
        profile, _ = Profile.objects.get_or_create(user=instance.user)
        if profile.vk_user_id != uid:
            profile.vk_user_id = uid
            profile.save(update_fields=['vk_user_id'])


_register_socialaccount_signal()
