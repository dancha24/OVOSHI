"""Сопоставление пользователя бота ВК с учёткой в БД (баланс ОК) по id ВК.

Основной сценарий — бот: при первом обращении создаётся пользователь с vk_user_id;
сайт используется для админки и при желании входа через ВК (SocialAccount).
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from .models import Profile

User = get_user_model()

_BOT_EMAIL_DOMAIN = 'bot.ovoshi.local'


def _unique_vk_username(vk_user_id: int) -> str:
    base = f'vk_{vk_user_id}'
    if not User.objects.filter(username=base).exists():
        return base
    for n in range(2, 1000):
        cand = f'vk_{vk_user_id}_{n}'
        if not User.objects.filter(username=cand).exists():
            return cand
    return f'vk_{vk_user_id}_u{User.objects.count()}'


def ensure_vk_player(vk_user_id: int) -> User:
    """Гарантирует User с profile.vk_user_id; при отсутствии — создаёт (роль гость, 0 ОК)."""
    u = resolve_user_by_vk_id(vk_user_id)
    if u:
        return u
    uid = int(vk_user_id)
    email = f'vk{uid}@{_BOT_EMAIL_DOMAIN}'
    try:
        with transaction.atomic():
            user = User(
                email=email,
                username=_unique_vk_username(uid),
                role=User.Role.GUEST,
                clan_points=0,
            )
            user.set_unusable_password()
            user.save()
            # post_save создаёт Profile через signals — второй create даёт duplicate user_id.
            Profile.objects.update_or_create(user=user, defaults={'vk_user_id': uid})
            return user
    except IntegrityError:
        u = resolve_user_by_vk_id(vk_user_id)
        if u:
            return u
        user = User.objects.filter(email=email).select_related('profile').first()
        if user:
            profile, _ = Profile.objects.get_or_create(user=user)
            if profile.vk_user_id != uid:
                profile.vk_user_id = uid
                profile.save(update_fields=['vk_user_id'])
            return user
        raise


def resolve_user_by_vk_id(vk_user_id: int) -> User | None:
    """Профиль.vk_user_id, затем SocialAccount (несколько вариантов provider / формата uid)."""
    if not vk_user_id or vk_user_id < 1:
        return None

    uid_str = str(vk_user_id).strip()

    u = (
        User.objects.filter(profile__vk_user_id=vk_user_id)
        .select_related('profile')
        .first()
    )
    if u:
        return u

    try:
        from allauth.socialaccount.models import SocialAccount
    except ImportError:
        return None

    def _attach(acc):
        profile, _ = Profile.objects.get_or_create(user=acc.user)
        if profile.vk_user_id != vk_user_id:
            profile.vk_user_id = vk_user_id
            profile.save(update_fields=['vk_user_id'])
        return acc.user

    for provider in ('vk', 'vk_oauth2'):
        acc = (
            SocialAccount.objects.filter(provider=provider, uid=uid_str)
            .select_related('user')
            .first()
        )
        if acc:
            return _attach(acc)

    # На случай иного строкового представления uid в БД
    for acc in SocialAccount.objects.filter(provider__in=('vk', 'vk_oauth2')).select_related('user'):
        try:
            if int(str(acc.uid).strip()) != vk_user_id:
                continue
        except (ValueError, TypeError):
            continue
        return _attach(acc)

    return None
