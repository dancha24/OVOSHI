"""
Слить двух пользователей: оставить один аккаунт (реальный email), перенести профиль/соц.сети/заявки, удалить второго.

Пример (ты + бот):
  python manage.py merge_users --keep-email dancha241@yandex.ru --drop-email vk37746302@bot.ovoshi.local
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import ClanApplication, Profile


class Command(BaseCommand):
    help = 'Объединить двух пользователей: оставить --keep-email, данные из --drop-email перенести и удалить второго.'

    def add_arguments(self, parser):
        parser.add_argument('--keep-email', required=True, dest='keep_email', help='Email аккаунта, который остаётся')
        parser.add_argument('--drop-email', required=True, dest='drop_email', help='Email аккаунта, который удаляется')

    def handle(self, *args, **options):
        User = get_user_model()
        keep_email = (options['keep_email'] or '').strip().lower()
        drop_email = (options['drop_email'] or '').strip().lower()
        if keep_email == drop_email:
            raise CommandError('Укажите два разных email.')

        try:
            u_keep = User.objects.get(email__iexact=keep_email)
        except User.DoesNotExist as e:
            raise CommandError(f'Нет пользователя с email {keep_email!r}.') from e
        try:
            u_drop = User.objects.get(email__iexact=drop_email)
        except User.DoesNotExist as e:
            raise CommandError(f'Нет пользователя с email {drop_email!r}.') from e

        with transaction.atomic():
            self._move_social_accounts(u_keep, u_drop)
            self._merge_profiles(u_keep, u_drop)
            self._move_email_addresses(u_keep, u_drop)
            ClanApplication.objects.filter(user=u_drop).update(user=u_keep)
            # Очки/карма: не терять максимум из двух аккаунтов
            if u_drop.clan_points > u_keep.clan_points or u_drop.karma > u_keep.karma:
                u_keep.clan_points = max(u_keep.clan_points, u_drop.clan_points)
                u_keep.karma = max(u_keep.karma, u_drop.karma)
                u_keep.save(update_fields=['clan_points', 'karma'])
            u_drop.delete()

        self.stdout.write(self.style.SUCCESS(f'Готово: оставлен {u_keep.email}, {drop_email} удалён.'))

    def _move_social_accounts(self, u_keep, u_drop):
        try:
            from allauth.socialaccount.models import SocialAccount
        except ImportError:
            return
        for sa in SocialAccount.objects.filter(user=u_drop):
            if SocialAccount.objects.filter(user=u_keep, provider=sa.provider, uid=sa.uid).exists():
                sa.delete()
                continue
            if SocialAccount.objects.filter(user=u_keep, provider=sa.provider).exists():
                self.stdout.write(
                    f'  У {u_keep.email} уже есть {sa.provider}, запись {sa.uid} у удаляемого снята.'
                )
                sa.delete()
                continue
            sa.user = u_keep
            sa.save(update_fields=['user_id'])

    def _merge_profiles(self, u_keep, u_drop):
        p_keep, _ = Profile.objects.get_or_create(user=u_keep)
        try:
            p_drop = u_drop.profile
        except Profile.DoesNotExist:
            p_keep.save()
            return
        for attr in ('nickname', 'uid', 'city', 'avatar'):
            v_drop = getattr(p_drop, attr, None)
            v_keep = getattr(p_keep, attr, None)
            if v_drop and not v_keep:
                setattr(p_keep, attr, v_drop)
        if p_drop.birth_date is not None and p_keep.birth_date is None:
            p_keep.birth_date = p_drop.birth_date
        # vk_user_id уникален глобально: сначала снять с удаляемого профиля, потом записать в оставляемый
        vk_take = None
        if p_drop.vk_user_id is not None and p_keep.vk_user_id is None:
            vk_take = p_drop.vk_user_id
            Profile.objects.filter(pk=p_drop.pk).update(vk_user_id=None)
        if vk_take is not None:
            p_keep.vk_user_id = vk_take
        p_keep.save()

    def _move_email_addresses(self, u_keep, u_drop):
        try:
            from allauth.account.models import EmailAddress
        except ImportError:
            return
        for ea in EmailAddress.objects.filter(user=u_drop):
            if EmailAddress.objects.filter(user=u_keep, email__iexact=ea.email).exists():
                ea.delete()
                continue
            ea.user = u_keep
            ea.save(update_fields=['user_id'])
